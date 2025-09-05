# Importando as bibliotecas necessárias
import streamlit as st
import google.generativeai as genai
from googleapiclient.discovery import build
import os
import re

# --- Carregamento das Chaves de API ---
# Use o sistema de segredos do Streamlit ou variáveis de ambiente
# Para teste local, você ainda pode usar o python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
except ImportError:
    # Se o dotenv não estiver instalado, tente pegar dos segredos do Streamlit (para deploy)
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Verificação das chaves
if not GEMINI_API_KEY or not YOUTUBE_API_KEY:
    st.error("ERRO: As chaves de API do Gemini e do YouTube não foram encontradas. Defina-as em suas variáveis de ambiente ou segredos do Streamlit.")
    st.stop() # Interrompe a execução do app se as chaves não existirem

# --- Configuração das APIs ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Erro ao configurar as APIs: {e}")
    st.stop()


# --- Funções Auxiliares (do script anterior) ---
def get_youtube_video_id(song_title, artist):
    query = f"{song_title} {artist} official audio"
    try:
        search_response = youtube.search().list(q=query, part='snippet', maxResults=1, type='video').execute()
        if search_response.get("items"):
            return search_response["items"][0]["id"]["videoId"]
    except Exception:
        # Silenciosamente falha para não poluir a interface com erros
        return None
    return None

def generate_playlist(user_input):
    """Função principal que interage com a IA e o YouTube."""
    prompt_completo = f"""
    Você é um "Music Sommelier", um especialista em curadoria musical de nicho, focado em conectar músicas com base em nuances e características sonoras específicas. Sua tarefa é criar uma playlist coesa e de alta qualidade.

    O usuário forneceu as seguintes preferências: "{user_input}"
    
    Siga estas regras RIGOROSAMENTE:
    
    1.  **Inclusão Obrigatória:** Se o usuário mencionou músicas ou artistas específicos, comece a playlist com eles. O restante da playlist deve complementar essas escolhas iniciais.
    2.  **Critérios de Seleção:** As músicas recomendadas DEVEM compartilhar características sonoras claras com as preferências do usuário. Concentre-se em:
        - **Subgênero:** Mantenha-se estritamente dentro do subgênero (ex: se for 'grunge', evite 'hard rock de arena').
        - **Instrumentação e Timbre:** Procure por timbres de guitarra, padrões de bateria ou linhas de baixo semelhantes.
        - **Período de Tempo:** Dê preferência a músicas da mesma era ou de movimentos musicais diretamente influenciados.
        - **"Vibe" e Atmosfera:** A energia e o sentimento da música devem ser compatíveis.
    3.  **Evitar Saltos Genéricos:** Não recomende artistas muito óbvios ou de gêneros completamente diferentes, a menos que haja uma conexão muito forte e específica.
    4.  **Formato de Saída:** A sua resposta final deve conter APENAS a lista de músicas. Para cada música, use o formato exato "Nome da Música | Nome do Artista", uma por linha. Não adicione números, marcadores, títulos, explicações ou qualquer texto introdutório. A playlist final deve ter um total de 8 a 10 músicas.
    """
    
    # Gerar recomendações com Gemini
    response = model.generate_content(prompt_completo)
    song_recommendations = response.text.strip().split('\n')
    
    video_ids = []
    # Usando st.status para mostrar o progresso na interface
    with st.status("Encontrando as músicas no YouTube...", expanded=True) as status:
        for line in song_recommendations:
            match = re.match(r"(.+?)\s*\|\s*(.+)", line)
            if match:
                song, artist = match.groups()
                song, artist = song.strip(), artist.strip()
                st.write(f"Buscando por '{song}' de '{artist}'...")
                video_id = get_youtube_video_id(song, artist)
                if video_id:
                    video_ids.append(video_id)
        
        if video_ids:
            status.update(label="Playlist criada com sucesso!", state="complete", expanded=False)
    
    if video_ids:
        playlist_ids_string = ",".join(video_ids)
        playlist_url = f"https://www.youtube.com/watch_videos?video_ids={playlist_ids_string}"
        return f"Playlist pronta! 🎧\n\n[Clique aqui para ouvir no YouTube]({playlist_url})"
    else:
        return "Desculpe, não consegui encontrar vídeos para as músicas recomendadas. Tente ser mais específico."


# --- Interface do Streamlit ---

# Título da página
st.set_page_config(page_title="Playlisto", page_icon="🎵")
st.title("Calma aí, playlisto 👐")
st.caption("Um chatbot para criar playlists no YouTube com base no seu gosto musical.")

# Inicializar o histórico do chat na memória da sessão
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! Descreva as bandas, músicas ou o estilo que você curte e eu criarei uma playlist para você."}]

# Exibir mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar a entrada do usuário
if prompt := st.chat_input("Ex: Rock alternativo dos anos 90 como Nirvana..."):
    # Adicionar a mensagem do usuário ao histórico e exibi-la
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gerar e exibir a resposta do bot
    with st.chat_message("assistant"):
        # Mostrar um indicador de "pensando..."
        with st.spinner("Criando sua playlist..."):
            response = generate_playlist(prompt)
        
        st.markdown(response)
    
    # Adicionar a resposta do bot ao histórico
    st.session_state.messages.append({"role": "assistant", "content": response})