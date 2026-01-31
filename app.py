import os
import re
import math
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple

from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, flash
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================
APP_NAME = "EthosPsi"
app = Flask(__name__)
# Chave secreta para sessões (flash messages)
app.config["SECRET_KEY"] = "dev-ethospsi-master-key-v5"

DATA_DIR = os.path.abspath("./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ethospsi.sqlite3")

# Configurações de indexação de texto
CHUNK_CHARS = 800  
CHUNK_OVERLAP = 100

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)

# =====================================================
# BANCO DE RESPOSTAS PRONTAS (CURADORIA ÉTICA)
# =====================================================
RESPOSTAS_PRONTAS = {
    # ---------------------------------------------------------
    # 🧭 SIGILO PROFISSIONAL
    # ---------------------------------------------------------
    "Até onde vai o sigilo quando o paciente relata um comportamento ilegal?": """
    <div class="resposta-humanizada">
        <h3>O sigilo protege o relato, não o crime. Mas há limites.</h3>
        <p>Se o paciente relata um crime <strong>já cometido</strong> (ex: roubou algo no passado, fraudou IR), o sigilo é absoluto. O psicólogo não é agente de segurança pública.</p>
        <p>O sigilo deve ser quebrado (Art. 10) apenas se houver <strong>risco grave e iminente</strong> à vida ou integridade física (ex: planejamento de homicídio, violência contra criança/idoso ou suicídio em curso).</p>
    </div>
    """,

    "O que fazer quando o paciente pede que você não registre algo no prontuário?": """
    <div class="resposta-humanizada">
        <h3>O registro é dever do psicólogo (Resolução 01/2009).</h3>
        <p>Você não pode deixar de registrar, mas pode usar a <strong>generalidade técnica</strong>.</p>
        <div class="alert-box tip">
            💡 <strong>Exemplo:</strong> Em vez de "Paciente traiu a esposa com a vizinha", registre "Paciente abordou conflitos conjugais e questões de fidelidade". Você cumpre a lei sem expor a intimidade desnecessária.
        </div>
    </div>
    """,

    "Como agir quando um familiar liga pedindo informações sobre o paciente?": """
    <div class="resposta-humanizada">
        <h3>Proteja a existência do tratamento.</h3>
        <p>Nunca confirme que a pessoa é sua paciente sem autorização. A resposta padrão ética é:</p>
        <p><em>"Por questões de sigilo profissional, não posso confirmar se essa pessoa é atendida aqui ou passar qualquer informação sobre pacientes."</em></p>
    </div>
    """,

    "O sigilo pode ser mantido mesmo diante de risco potencial e ainda incerto?": """
    <div class="resposta-humanizada">
        <h3>Sim. O risco precisa ser atual e grave.</h3>
        <p>A quebra de sigilo baseia-se na busca do <strong>menor prejuízo</strong>. Se o risco é apenas uma ideia vaga ("tenho vontade de sumir"), trabalha-se isso em sessão. A quebra ocorre quando o risco se torna <strong>iminente</strong> (plano concreto + meios acessíveis).</p>
    </div>
    """,

    "Como manejar o sigilo em atendimentos online feitos em ambiente não controlado?": """
    <div class="resposta-humanizada">
        <h3>Contrato e tecnologia.</h3>
        <p>Exija o uso de fones de ouvido. Se o paciente estiver em local público ou sem privacidade (família perto), é dever do psicólogo interromper ou remarcar a sessão para proteger o sigilo dele, mesmo que ele diga que "não tem problema".</p>
    </div>
    """,

    "É ético discutir um caso clínico em supervisão sem autorização explícita do paciente?": """
    <div class="resposta-humanizada">
        <h3>Sim, desde que com anonimato total.</h3>
        <p>A supervisão visa qualificar o serviço (Art. 1º 'c'). Você não precisa de autorização para estudar o caso, mas tem o dever ético de <strong>omitir qualquer dado identificável</strong> (nome, empresa, cidade) para preservar a identidade.</p>
    </div>
    """,

    "O que fazer quando o paciente revela algo grave sobre terceiros?": """
    <div class="resposta-humanizada">
        <h3>Avalie a vulnerabilidade.</h3>
        <p>Se o terceiro for criança, adolescente ou idoso sofrendo violência, a notificação é compulsória (ECA/Estatuto do Idoso) e se sobrepõe ao sigilo. Se for conflito entre adultos capazes, o sigilo prevalece e o trabalho é clínico.</p>
    </div>
    """,

    "Como lidar com pedidos de prontuário feitos por advogados?": """
    <div class="resposta-humanizada">
        <h3>O documento pertence ao paciente.</h3>
        <p>Você fornece o documento ao <strong>paciente</strong> se ele solicitar. Se o advogado pedir, diga que precisa da solicitação direta do paciente. Se for ordem judicial, entregue em envelope lacrado marcado "Confidencial".</p>
    </div>
    """,

    "Existe diferença ética entre sigilo clínico e sigilo institucional?": """
    <div class="resposta-humanizada">
        <h3>O escopo muda (Art. 6º).</h3>
        <p>Em equipes multiprofissionais, você compartilha apenas o <strong>estritamente necessário</strong> para a condução conjunta do caso. Detalhes íntimos que não afetam a conduta médica/escolar ficam restritos ao psicólogo.</p>
    </div>
    """,

    "O que caracteriza quebra de sigilo “necessária” e “excessiva”?": """
    <div class="resposta-humanizada">
        <h3>Critério do Menor Prejuízo.</h3>
        <ul>
            <li><strong>Necessária:</strong> Avisar família sobre risco de suicídio iminente.</li>
            <li><strong>Excessiva:</strong> Avisar sobre o risco E contar detalhes das mágoas ou segredos que não têm relação com a proteção da vida.</li>
        </ul>
    </div>
    """,

    # ---------------------------------------------------------
    # ⚖️ LIMITES DA ATUAÇÃO PROFISSIONAL
    # ---------------------------------------------------------
    "Quando uma orientação ultrapassa o limite da psicoterapia e vira aconselhamento indevido?": """
    <div class="resposta-humanizada">
        <h3>Quando você decide pelo outro.</h3>
        <p>Torna-se indevido quando você diz o que o paciente <em>deve</em> fazer ("Separe dele", "Peça demissão"). O papel é promover autonomia para que ele decida.</p>
    </div>
    """,

    "É ético sugerir decisões práticas de vida ao paciente?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>Salvo risco de vida, sugerir decisões práticas cria dependência. O psicólogo analisa consequências, mas a decisão é do sujeito.</p>
    </div>
    """,

    "Como reconhecer quando o psicólogo está atuando fora de sua competência técnica?": """
    <div class="resposta-humanizada">
        <h3>Sinais de Alerta:</h3>
        <p>Sentimento de estar perdido, angústia pré-sessão ou estagnação do caso por falta de base teórica (ex: atender Transtorno Alimentar grave sem estudo). Insistir sem preparo é imprudência (Art. 1º 'b').</p>
    </div>
    """,

    "O que fazer quando o paciente pede um parecer para fins judiciais?": """
    <div class="resposta-humanizada">
        <h3>Não misture papéis (Resolução 08/2010).</h3>
        <p>Se você é psicoterapeuta, não deve atuar como perito do próprio paciente. O laudo assistencial é parcial. Se necessário, emita apenas um relatório ou declaração de acompanhamento.</p>
    </div>
    """,

    "É ético atender demandas que exigem formação que o profissional ainda não possui?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>É vedado assumir responsabilidades para as quais não esteja capacitado. Encaminhe para um especialista.</p>
    </div>
    """,

    "Quando encaminhar deixa de ser opção e se torna obrigação ética?": """
    <div class="resposta-humanizada">
        <h3>Três situações principais:</h3>
        <ol>
            <li>Falta de competência técnica para a demanda.</li>
            <li>Conflito pessoal que impede a neutralidade.</li>
            <li>Ausência de evolução terapêutica prolongada.</li>
        </ol>
    </div>
    """,

    "É ético atender um paciente apenas por necessidade financeira?": """
    <div class="resposta-humanizada">
        <h3>Não. É vedado (Art. 2º 'n').</h3>
        <p>Prolongar tratamento desnecessariamente fere a integridade da profissão e lesa o paciente.</p>
    </div>
    """,

    "Até onde o psicólogo pode intervir em conflitos familiares?": """
    <div class="resposta-humanizada">
        <h3>Foco no paciente.</h3>
        <p>Você não é juiz. Pode convidar familiares para orientação pontual (com aval do paciente), mas não deve agir como mediador de quem "tem razão".</p>
    </div>
    """,

    "O que caracteriza exercício irregular da profissão dentro da clínica?": """
    <div class="resposta-humanizada">
        <h3>Técnicas não reconhecidas.</h3>
        <p>Usar Tarô, Reiki, Florais ou práticas religiosas/esotéricas dentro da sessão de psicologia é falta ética grave (Art. 1º 'c').</p>
    </div>
    """,

    "A neutralidade é uma exigência ética ou um mito clínico?": """
    <div class="resposta-humanizada">
        <h3>Neutralidade absoluta é mito; Imparcialidade é dever.</h3>
        <p>Você tem valores, mas a ética exige que não atue <em>em função</em> deles. O foco é a demanda do sujeito, acolhida sem julgamento moral.</p>
    </div>
    """,

    # ---------------------------------------------------------
    # 🔄 RELAÇÕES DUAIS E CONFLITOS DE INTERESSE
    # ---------------------------------------------------------
    "É ético atender amigos ou conhecidos?": """
    <div class="resposta-humanizada">
        <h3>Não recomendado.</h3>
        <p>A relação pessoal prévia contamina a transferência e a isenção necessária. Configure relação dual que prejudica o processo.</p>
    </div>
    """,

    "O que caracteriza uma relação dual problemática?": """
    <div class="resposta-humanizada">
        <h3>Dois papéis simultâneos.</h3>
        <p>Ex: Ser psicólogo e chefe; psicólogo e professor (que dá nota); psicólogo e parceiro de negócios.</p>
    </div>
    """,

    "Como lidar quando o paciente começa a oferecer favores ou presentes?": """
    <div class="resposta-humanizada">
        <h3>Analise a função.</h3>
        <p>É gratidão ou sedução/compra? Recuse favores que gerem dívida simbólica. Presentes pequenos podem ser aceitos se a recusa for mais danosa ao vínculo.</p>
    </div>
    """,

    "É ético manter contato com pacientes nas redes sociais?": """
    <div class="resposta-humanizada">
        <h3>Perfil Profissional: Sim. Pessoal: Não.</h3>
        <p>Seguir o paciente no seu perfil íntimo expõe sua privacidade e quebra o enquadre. Mantenha interações no perfil profissional.</p>
    </div>
    """,

    "O que fazer quando o psicólogo cruza socialmente com o paciente?": """
    <div class="resposta-humanizada">
        <h3>Discrição total.</h3>
        <p>Não cumprimente efusivamente. Espere a reação do paciente. Se ele não falar, respeite o sigilo dele perante terceiros.</p>
    </div>
    """,

    "É possível uma relação terapêutica ética após uma relação prévia?": """
    <div class="resposta-humanizada">
        <h3>Risco altíssimo.</h3>
        <p>Se já houve intimidade ou conflito, a imagem do profissional já está "contaminada", dificultando a projeção necessária para a terapia.</p>
    </div>
    """,

    "Como agir quando o paciente demonstra interesse afetivo ou sexual?": """
    <div class="resposta-humanizada">
        <h3>Manejo clínico.</h3>
        <p>Não corresponda, mas acolha como material de trabalho (transferência). Ajude a entender o significado disso. Se houver assédio ou risco, encaminhe.</p>
    </div>
    """,

    "O que configura exploração da relação terapêutica?": """
    <div class="resposta-humanizada">
        <h3>Benefício próprio.</h3>
        <p>Ex: Pedir votos, vender produtos, pedir favores pessoais ou usar a influência para obter vantagens sexuais.</p>
    </div>
    """,

    "É ético atender familiares de ex-pacientes?": """
    <div class="resposta-humanizada">
        <h3>Zona de Risco.</h3>
        <p>Se o atendimento anterior foi recente ou envolveu dinâmicas familiares, evite. O sigilo do ex-paciente pode ficar comprometido na sua escuta.</p>
    </div>
    """,

    "Como identificar conflitos de interesse sutis na prática clínica?": """
    <div class="resposta-humanizada">
        <h3>Sinais internos:</h3>
        <p>Você evita certos temas por medo de perder o paciente (financeiro)? Você torce excessivamente por um desfecho na vida dele? Isso indica perda de isenção.</p>
    </div>
    """,

    # ---------------------------------------------------------
    # 💬 COMUNICAÇÃO, POSTURA E MANEJO CLÍNICO
    # ---------------------------------------------------------
    "Existe limite ético para a autorrevelação do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Sim: O benefício do paciente.</h3>
        <p>Falar de si só é válido se tiver objetivo terapêutico. Desabafar problemas ou contar vantagens pessoais é falha técnica.</p>
    </div>
    """,

    "Quando o silêncio pode ser eticamente problemático?": """
    <div class="resposta-humanizada">
        <h3>Quando é abandono.</h3>
        <p>O silêncio técnico é ferramenta. O silêncio porque você não sabe o que fazer ou está irritado é negligência.</p>
    </div>
    """,

    "Como manejar discordâncias de valores sem impor crenças pessoais?": """
    <div class="resposta-humanizada">
        <h3>Validação.</h3>
        <p>Você não precisa concordar, precisa entender a função daquilo para o sujeito. Impor sua visão política ou religiosa é vedado (Art. 2º 'b').</p>
    </div>
    """,

    "É ético confrontar diretamente o paciente?": """
    <div class="resposta-humanizada">
        <h3>Sim, tecnicamente.</h3>
        <p>Confrontar contradições é trabalho. Ser agressivo, irônico ou moralista é desrespeito.</p>
    </div>
    """,

    "Como agir quando o paciente questiona a competência do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Não ataque.</h3>
        <p>Acolha a dúvida. Pode ser resistência ou uma falha real sua. Analise com humildade e, se necessário, supervisione.</p>
    </div>
    """,

    "O que caracteriza uma postura clínica respeitosa?": """
    <div class="resposta-humanizada">
        <h3>Além da educação.</h3>
        <p>É pontualidade, não atender mexendo no celular, garantir isolamento acústico e escuta ativa.</p>
    </div>
    """,

    "É ético prolongar um processo terapêutico sem ganhos claros?": """
    <div class="resposta-humanizada">
        <h3>Não (Art. 2º 'n').</h3>
        <p>Se estagnou, rediscuta objetivos, dê alta ou encaminhe.</p>
    </div>
    """,

    "Quando a frustração do psicólogo interfere eticamente na clínica?": """
    <div class="resposta-humanizada">
        <h3>Acting-out do terapeuta.</h3>
        <p>Se você começa a ser ríspido ou esquecer sessões por frustração, busque supervisão. Você pode estar prejudicando o paciente.</p>
    </div>
    """,

    "O que fazer quando o psicólogo percebe antipatia pelo paciente?": """
    <div class="resposta-humanizada">
        <h3>Supervisão e Análise.</h3>
        <p>Se o sentimento impedir o acolhimento, é mais ético encaminhar do que atender de má vontade.</p>
    </div>
    """,

    "Como manejar erros cometidos durante o processo terapêutico?": """
    <div class="resposta-humanizada">
        <h3>Transparência e reparação.</h3>
        <p>Errou? Reconheça, peça desculpas e trabalhe o impacto disso na relação. A onipotência é prejudicial.</p>
    </div>
    """,

    # ---------------------------------------------------------
    # 🧠 AUTONOMIA, RESPONSABILIDADE E CUIDADO
    # ---------------------------------------------------------
    "Como respeitar a autonomia do paciente em escolhas autodestrutivas?": """
    <div class="resposta-humanizada">
        <h3>Limite: Capacidade civil e Risco de Vida.</h3>
        <p>Se o paciente é capaz e não há risco de morte, ele tem direito a escolhas ruins. O psicólogo aponta, mas não proíbe.</p>
    </div>
    """,

    "Quando o cuidado justifica uma intervenção mais diretiva?": """
    <div class="resposta-humanizada">
        <h3>Crise e Perda de Crítica.</h3>
        <p>Surto, risco de suicídio, abuso grave de substâncias. A proteção à vida se sobrepõe temporariamente à autonomia.</p>
    </div>
    """,

    "É ético continuar atendendo um paciente que não deseja mudanças?": """
    <div class="resposta-humanizada">
        <h3>Depende do contrato.</h3>
        <p>Se a demanda é apenas suporte/manutenção, ok. Se não há função terapêutica, discuta a alta.</p>
    </div>
    """,

    "Como lidar com demandas que contrariam princípios pessoais do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Encaminhamento responsável.</h3>
        <p>Se você não consegue acolher (ex: aborto, religião) por convicção pessoal, reconheça a limitação e encaminhe para quem acolha sem julgamento.</p>
    </div>
    """,

    "O que caracteriza negligência ética na clínica?": """
    <div class="resposta-humanizada">
        <h3>Omissão.</h3>
        <p>Ignorar risco de suicídio, não fazer prontuário, faltar sem avisar, deixar paciente sem respaldo em crise.</p>
    </div>
    """,

    "Quando a desistência do atendimento é eticamente justificável?": """
    <div class="resposta-humanizada">
        <h3>Ameaça ou limite técnico.</h3>
        <p>Você não é obrigado a atender quem te agride ou ameaça. Encerre garantindo apenas o encaminhamento seguro.</p>
    </div>
    """,

    "Como lidar com faltas e inadimplência sem violar a ética?": """
    <div class="resposta-humanizada">
        <h3>Contrato claro.</h3>
        <p>Cobrar faltas é ético se foi combinado. A cobrança de dívidas deve ser respeitosa, sem expor o paciente (Art. 4º).</p>
    </div>
    """,

    "O que é responsabilidade ética na clínica além do Código?": """
    <div class="resposta-humanizada">
        <h3>Compromisso Social.</h3>
        <p>É combater preconceitos, entender o contexto social do sofrimento e não patologizar a pobreza ou diversidade.</p>
    </div>
    """,

    "É ético atender pacientes em sofrimento intenso sem suporte de rede?": """
    <div class="resposta-humanizada">
        <h3>Desafiador, mas ético.</h3>
        <p>Ajude a construir a rede (CAPS, Assistência Social). Não abandone por ser "difícil", mas não tente ser a única rede dele.</p>
    </div>
    """,

    "Como a ética se manifesta nas pequenas decisões cotidianas da clínica?": """
    <div class="resposta-humanizada">
        <h3>Nos detalhes.</h3>
        <p>No isolamento acústico da sala, na guarda do prontuário, na pontualidade, no estudo do caso.</p>
    </div>
    """,
    
    # ---------------------------------------------------------
    # RESPOSTAS ADICIONAIS ANTERIORES (MANTIDAS PELA RELEVÂNCIA)
    # ---------------------------------------------------------
    "Posso atender de graça?": """
    <div class="resposta-humanizada">
        <h3>Pode (Pro bono).</h3>
        <p>O vedado é usar o preço baixo como propaganda ("Terapia a R$10"). Se for voluntário, mantenha o mesmo rigor técnico.</p>
    </div>
    """,
    
    "Posso influenciar na orientação sexual do meu paciente?": """
    <div class="resposta-humanizada">
        <h3>JAMAIS.</h3>
        <p>É infração ética grave (Art. 2º 'b') induzir convicções ou tentar "reverter" orientação sexual.</p>
    </div>
    """,
    
    "Existe psicologia evangélica?": """
    <div class="resposta-humanizada">
        <h3>Não como ciência.</h3>
        <p>A Psicologia é laica. Você pode ser cristão, mas sua técnica não pode ser religiosa (orar em sessão, catequizar).</p>
    </div>
    """,

    "Eu sou obrigada fazer anotações?": """
    <div class="resposta-humanizada">
        <h3>Sim.</h3>
        <p>O prontuário é obrigatório (Res. 01/2009) para todos os pacientes.</p>
    </div>
    """
}

# =====================================================
# SELEÇÃO DE BOTÕES RÁPIDOS (PRIORIDADE: RESPOSTAS DIRETAS)
# =====================================================
QUICK_QUESTIONS = [
    "Até onde vai o sigilo em caso de crime?",
    "Paciente pediu para não registrar no prontuário",
    "Posso atender familiares de ex-pacientes?",
    "Eu sou obrigada fazer anotações?",
    "Posso atender de graça?",
    "Como lidar com inadimplência?",
    "Posso aceitar presentes?",
    "Devo cumprimentar meu paciente na rua?",
    "O que fazer se o juiz pedir o prontuário?"
]

# =====================================================
# DADOS BASE (PARA BUSCA GENÉRICA - REFORÇO)
# =====================================================
TEXTO_CODIGO_ETICA = """
PRINCÍPIOS FUNDAMENTAIS
I. O psicólogo baseará o seu trabalho no respeito e na promoção da liberdade, da dignidade, da igualdade e da integridade do ser humano.
II. O psicólogo trabalhará visando promover a saúde e a qualidade de vida.
DAS RESPONSABILIDADES DO PSICÓLOGO - Art. 1º São deveres fundamentais:
b) Assumir responsabilidades profissionais somente por atividades para as quais esteja capacitado pessoal, teórica e tecnicamente.
c) Prestar serviços psicológicos de qualidade, utilizando princípios fundamentados na ciência psicológica, na ética e na legislação.
j) Ter, para com o trabalho dos psicólogos e de outros profissionais, respeito, consideração e solidariedade.
Art. 2º Ao psicólogo é vedado:
a) Praticar ou ser conivente com quaisquer atos que caracterizem negligência, discriminação, exploração, violência, crueldade ou opressão.
b) Induzir a convicções políticas, filosóficas, morais, ideológicas, religiosas, de orientação sexual ou a qualquer tipo de preconceito.
j) Estabelecer com a pessoa atendida, familiar ou terceiro, relação que possa interferir negativamente nos objetivos do serviço prestado.
n) Prolongar, desnecessariamente, a prestação de serviços profissionais.
SIGILO PROFISSIONAL
Art. 9º - É dever do psicólogo respeitar o sigilo profissional a fim de proteger, por meio da confidencialidade, a intimidade das pessoas.
Art. 10 - Nas situações em que se configure conflito entre as exigências decorrentes do disposto no Art. 9º e as afirmações dos princípios fundamentais deste Código, excetuando-se os casos previstos em lei, o psicólogo poderá decidir pela quebra de sigilo, baseando sua decisão na busca do menor prejuízo.
"""

# =====================================================
# FUNÇÕES DE BANCO DE DADOS
# =====================================================
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, title TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, doc_id INTEGER, chunk_text TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS qa_history (id INTEGER PRIMARY KEY, question TEXT, answer TEXT, created_at TEXT)""")
    conn.commit()
    conn.close()

def clear_documents():
    conn = db()
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM documents")
    conn.commit()
    conn.close()

def save_history(question: str, answer: str):
    conn = db()
    conn.execute("INSERT INTO qa_history (question, answer, created_at) VALUES (?,?,?)",
                 (question, answer, datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

def get_history(limit: int = 50):
    conn = db()
    rows = conn.execute("SELECT * FROM qa_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def stats():
    conn = db()
    try:
        d = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        h = conn.execute("SELECT COUNT(*) FROM qa_history").fetchone()[0]
    except:
        return {"documents": 0, "chunks": 0, "history": 0}
    conn.close()
    return {"documents": d, "chunks": c, "history": h}

# =====================================================
# LÓGICA DE BUSCA
# =====================================================
def index_content(title: str, text: str):
    chunks = [c.strip() for c in text.split('\n') if len(c.strip()) > 20]
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO documents (title, created_at) VALUES (?,?)", (title, datetime.now().strftime("%Y-%m-%d")))
    doc_id = cur.lastrowid
    for c in chunks:
        cur.execute("INSERT INTO chunks (doc_id, chunk_text) VALUES (?,?)", (doc_id, c))
    conn.commit()
    conn.close()

def simple_search(query: str):
    conn = db()
    terms = query.lower().split()
    keywords = [t for t in terms if len(t) > 3] 
    
    if not keywords: return []

    sql = "SELECT chunk_text FROM chunks WHERE " + " OR ".join(["chunk_text LIKE ?"] * len(keywords))
    params = [f"%{k}%" for k in keywords]
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    seen = set()
    unique_rows = []
    for r in rows:
        if r[0] not in seen:
            unique_rows.append(r[0])
            seen.add(r[0])
    return unique_rows[:3]

# =====================================================
# ROTAS DO FLASK
# =====================================================
@app.route("/", methods=["GET", "POST"])
def home():
    answer = None
    
    if request.method == "POST":
        # 1. Resetar Base
        if "load_bases" in request.form:
            clear_documents()
            index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
            flash("Cérebro ético atualizado com sucesso!", "success")
            return redirect(url_for('home'))

        # 2. Processar Pergunta
        q = request.form.get("q", "").strip()
        
        if q:
            # A) Tenta Match Exato (Prioridade Máxima)
            if q in RESPOSTAS_PRONTAS:
                answer = RESPOSTAS_PRONTAS[q]
            
            # B) Tenta Match Parcial (Inteligente)
            else:
                found_partial = False
                for key, val in RESPOSTAS_PRONTAS.items():
                    key_clean = key.lower().replace("?","")
                    q_clean = q.lower().replace("?","")
                    
                    # Lógica 1: Se a pergunta do usuário estiver CONTIDA na chave (ex: "atender de graça" está em "Posso atender de graça?")
                    if q_clean in key_clean:
                         answer = val
                         found_partial = True
                         break
                    
                    # Lógica 2: Interseção de palavras (se coincidir muitas palavras importantes)
                    key_words = set(key_clean.split())
                    q_words = set(q_clean.split())
                    common = key_words.intersection(q_words)
                    
                    # Se tiver mais de 60% de palavras em comum com a pergunta cadastrada
                    if len(common) >= len(key_words) * 0.6:
                         answer = val
                         found_partial = True
                         break
                
                # C) Busca Genérica no Texto (Fallback)
                if not found_partial:
                    hits = simple_search(q)
                    if hits:
                        html_hits = "".join([f"<div class='ref-card source-cfp'><div class='ref-body'>...{h}...</div></div>" for h in hits])
                        answer = f"""
                        <div class="resposta-humanizada">
                            <h3>Resultados da Busca</h3>
                            <p>Não encontrei uma resposta pronta exata, mas veja o que o Código diz sobre temas relacionados:</p>
                            {html_hits}
                            <div class="alert-box tip">💡 Tente simplificar a pergunta ou usar os botões de sugestão.</div>
                        </div>
                        """
                    else:
                        answer = """
                        <div class="resposta-humanizada">
                            <h3>🤔 Dúvida não encontrada.</h3>
                            <div class="alert-box warning">
                                Não encontrei uma resposta específica no meu banco de dados atual.
                            </div>
                            <p>Tente clicar em um dos botões abaixo para ver exemplos de perguntas que eu sei responder.</p>
                        </div>
                        """
            
            save_history(q, answer)

    return render_template("home.html", 
                         app_name=APP_NAME, 
                         stats=stats(), 
                         history=get_history(50), 
                         answer=answer,
                         quick_questions=QUICK_QUESTIONS)

@app.route("/admin")
def admin():
    return render_template("admin.html", stats=stats(), app_name=APP_NAME)

if __name__ == "__main__":
    init_db()
    if stats()["chunks"] == 0:
        index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
    app.run(debug=True, port=5000)
