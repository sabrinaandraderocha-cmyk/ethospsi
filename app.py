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
app.config["SECRET_KEY"] = "dev-ethospsi-secret-master-v4"

DATA_DIR = os.path.abspath("./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ethospsi.sqlite3")

# Ajuste para busca no texto
CHUNK_CHARS = 800  
CHUNK_OVERLAP = 100

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)

# =====================================================
# RESPOSTAS PRONTAS (BASE DE CONHECIMENTO CLÍNICO/ÉTICO)
# =====================================================
RESPOSTAS_PRONTAS = {
    # ---------------------------------------------------------
    # 🧭 SIGILO PROFISSIONAL
    # ---------------------------------------------------------
    "Até onde vai o sigilo quando o paciente relata um comportamento ilegal?": """
    <div class="resposta-humanizada">
        <h3>O sigilo protege o relato, não o crime. Mas cuidado.</h3>
        <p>Se o paciente relata um crime <strong>já cometido</strong> (ex: roubou algo no passado), o sigilo é absoluto. O psicólogo não é policial nem juiz.</p>
        <p>O sigilo só pode (e deve) ser quebrado se houver <strong>risco iminente e grave</strong> à vida ou integridade física do paciente ou de terceiros (Art. 10), como em casos de violência contra criança, idoso ou ameaça concreta de homicídio/suicídio.</p>
    </div>
    """,

    "O que fazer quando o paciente pede que você não registre algo no prontuário?": """
    <div class="resposta-humanizada">
        <h3>O registro é dever do psicólogo, não escolha do paciente.</h3>
        <p>Você é obrigada pela Resolução CFP 01/2009 a manter o prontuário atualizado. Porém, você pode usar a técnica da <strong>generalidade ética</strong>.</p>
        <div class="alert-box tip">
            💡 <strong>Como fazer:</strong> Em vez de escrever "Paciente traiu a esposa com a vizinha", registre "Paciente trouxe questões relativas a conflitos conjugais e extraconjugais". Você registra o tema técnico sem expor a intimidade desnecessária.
        </div>
    </div>
    """,

    "Como agir quando um familiar liga pedindo informações sobre o paciente?": """
    <div class="resposta-humanizada">
        <h3>Proteja a existência do tratamento.</h3>
        <p>Se você confirmar que a pessoa é paciente, já está quebrando o sigilo. A resposta padrão deve ser: <em>"Por questões éticas e de sigilo, não posso confirmar se essa pessoa é atendida aqui ou passar qualquer informação."</em></p>
        <p>Se o paciente for criança/adolescente, você fala com os responsáveis, mas apenas o estritamente necessário (Art. 13).</p>
    </div>
    """,

    "O sigilo pode ser mantido mesmo diante de risco potencial e ainda incerto?": """
    <div class="resposta-humanizada">
        <h3>Sim. O risco precisa ser atual e grave.</h3>
        <p>A quebra de sigilo (Art. 10) é baseada na busca do <strong>menor prejuízo</strong>. Se o risco é apenas uma hipótese vaga ("tenho vontade de sumir"), trabalha-se isso em sessão.</p>
        <p>A quebra ocorre quando o risco se torna <strong>iminente</strong> (planejamento, meios acessíveis, intenção clara). Na dúvida, recorra à supervisão ou COF sem identificar o paciente.</p>
    </div>
    """,

    "Como manejar o sigilo em atendimentos online feitos em ambiente não controlado?": """
    <div class="resposta-humanizada">
        <h3>Contrato e tecnologia.</h3>
        <p>Oriente o paciente a usar fones de ouvido e estar em local privado. Se ele estiver em local público ou com família perto, é dever do psicólogo interromper ou remarcar a sessão para proteger o sigilo dele, mesmo que ele diga que "não tem problema".</p>
    </div>
    """,

    "É ético discutir um caso clínico em supervisão sem autorização explícita do paciente?": """
    <div class="resposta-humanizada">
        <h3>Sim, desde que com anonimato total.</h3>
        <p>A supervisão visa aprimorar o atendimento (Art. 1º 'c'). Você não precisa pedir permissão para se qualificar, mas tem o dever ético de <strong>omitir qualquer dado identificável</strong> (nome, empresa específica, cidade pequena) para que o supervisor foque no manejo, não na pessoa.</p>
    </div>
    """,

    "O que fazer quando o paciente revela algo grave sobre terceiros?": """
    <div class="resposta-humanizada">
        <h3>Avalie a vulnerabilidade da vítima.</h3>
        <p>Se o terceiro for criança, adolescente ou idoso sofrendo violência (ECA/Estatuto do Idoso), a notificação é compulsória e se sobrepõe ao sigilo. Se for um conflito entre adultos capazes, o sigilo prevalece e o trabalho é clínico, visando a responsabilização do paciente.</p>
    </div>
    """,

    "Como lidar com pedidos de prontuário feitos por advogados?": """
    <div class="resposta-humanizada">
        <h3>O prontuário pertence ao paciente, não ao advogado.</h3>
        <p>Você só fornece documentos se o <strong>próprio paciente</strong> solicitar. Se o advogado pedir, diga que precisa da solicitação direta do paciente.</p>
        <p>Se for ordem judicial, entregue em envelope lacrado marcado como "Confidencial".</p>
    </div>
    """,

    "Existe diferença ética entre sigilo clínico e sigilo institucional?": """
    <div class="resposta-humanizada">
        <h3>O sigilo é do psicólogo, mas o escopo muda.</h3>
        <p>Em instituições (hospitais, empresas), você pode compartilhar informações com a equipe multiprofissional, mas <strong>apenas o necessário</strong> para a condução conjunta do caso (Art. 6º). Detalhes íntimos que não afetam a conduta médica/escolar devem ficar restritos ao psicólogo.</p>
    </div>
    """,

    "O que caracteriza quebra de sigilo “necessária” e “excessiva”?": """
    <div class="resposta-humanizada">
        <h3>O critério é o "Menor Prejuízo".</h3>
        <ul>
            <li><strong>Necessária:</strong> Informar a família que há risco de suicídio.</li>
            <li><strong>Excessiva:</strong> Informar a família sobre o risco E contar detalhes de mágoas, traições ou fantasias que não têm relação direta com a proteção da vida.</li>
        </ul>
    </div>
    """,

    # ---------------------------------------------------------
    # ⚖️ LIMITES DA ATUAÇÃO PROFISSIONAL
    # ---------------------------------------------------------
    "Quando uma orientação ultrapassa o limite da psicoterapia e vira aconselhamento indevido?": """
    <div class="resposta-humanizada">
        <h3>Psicólogo promove autonomia, não decide pelo outro.</h3>
        <p>Vira "conselho indevido" quando você diz o que o paciente <em>deve</em> fazer ("Separe dele", "Peça demissão"). O papel é ajudar o paciente a entender as consequências e decidir por si mesmo.</p>
    </div>
    """,

    "É ético sugerir decisões práticas de vida ao paciente?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>Salvo em situações de risco de vida, sugerir decisões práticas ("Venda sua casa", "Mude de emprego") cria dependência e retira a responsabilidade do sujeito. Trabalhe para que <em>ele</em> chegue à conclusão.</p>
    </div>
    """,

    "Como reconhecer quando o psicólogo está atuando fora de sua competência técnica?": """
    <div class="resposta-humanizada">
        <h3>Autoanálise constante.</h3>
        <p>Se você se sente perdido, angustiado antes da sessão, ou percebe que o caso não evolui porque falta base teórica específica (ex: Transtorno Alimentar grave, Autismo), você deve encaminhar. Insistir sem preparo é imprudência (Art. 1º 'b').</p>
    </div>
    """,

    "O que fazer quando o paciente pede um parecer para fins judiciais?": """
    <div class="resposta-humanizada">
        <h3>Cuidado: Não misture papéis.</h3>
        <p>Se você é psicoterapeuta da pessoa, não deve atuar como perito dela (Resolução CFP 08/2010). O laudo assistencial é parcial (baseado no relato do paciente). Explique a diferença e, se necessário, faça apenas um relatório informativo de acompanhamento, nunca um laudo pericial conclusivo.</p>
    </div>
    """,

    "É ético atender demandas que exigem formação que o profissional ainda não possui?": """
    <div class="resposta-humanizada">
        <h3>Não. É vedado pelo Art. 1º 'b'.</h3>
        <p>Você só deve assumir responsabilidades para as quais esteja capacitado pessoal, teórica e tecnicamente. Se não sabe manejar, encaminhe.</p>
    </div>
    """,

    "Quando encaminhar deixa de ser opção e se torna obrigação ética?": """
    <div class="resposta-humanizada">
        <h3>Em três situações principais:</h3>
        <ol>
            <li>Falta de competência técnica para a demanda.</li>
            <li>Conflito pessoal que impede a neutralidade (ex: paciente agressor sexual e você foi vítima recentemente).</li>
            <li>Ausência de evolução terapêutica prolongada.</li>
        </ol>
    </div>
    """,

    "É ético atender um paciente apenas por necessidade financeira?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>Prolongar tratamento desnecessariamente (Art. 2º 'n') ou aceitar casos que você não pode ajudar apenas pelo dinheiro fere a integridade da profissão e lesa o paciente.</p>
    </div>
    """,

    "Até onde o psicólogo pode intervir em conflitos familiares?": """
    <div class="resposta-humanizada">
        <h3>Apenas no que tange ao seu paciente.</h3>
        <p>Você pode convidar familiares para sessões pontuais de orientação (com autorização do paciente), mas não deve agir como juiz, advogado ou "levar recados". O foco é a dinâmica relacional, não quem tem razão.</p>
    </div>
    """,

    "O que caracteriza exercício irregular da profissão dentro da clínica?": """
    <div class="resposta-humanizada">
        <h3>Uso de técnicas não reconhecidas.</h3>
        <p>Usar Tarô, Florais, Reiki, Constelação Familiar (não reconhecida pelo CFP) ou cunho religioso dentro da sessão de psicologia é falta ética (Art. 1º 'c' e Art. 2º 'f').</p>
    </div>
    """,

    "A neutralidade é uma exigência ética ou um mito clínico?": """
    <div class="resposta-humanizada">
        <h3>A neutralidade absoluta é um mito; a imparcialidade é dever.</h3>
        <p>Você sente coisas, tem valores. A ética exige que você não atue <em>em função</em> desses valores pessoais, mas sim em prol da demanda do sujeito. Você acolhe sem julgar, mesmo que discorde internamente.</p>
    </div>
    """,

    # ---------------------------------------------------------
    # 🔄 RELAÇÕES DUAIS E CONFLITOS
    # ---------------------------------------------------------
    "É ético atender amigos ou conhecidos?": """
    <div class="resposta-humanizada">
        <h3>Não recomendado.</h3>
        <p>A relação pessoal prévia contamina a transferência e a neutralidade. É uma relação dual que geralmente prejudica o andamento clínico e a amizade.</p>
    </div>
    """,

    "O que caracteriza uma relação dual problemática?": """
    <div class="resposta-humanizada">
        <h3>Quando há dois papéis simultâneos.</h3>
        <p>Ex: Ser psicólogo e chefe; psicólogo e professor (avaliador); psicólogo e sócio. O poder ou interesse de uma relação interfere na isenção da outra.</p>
    </div>
    """,

    "Como lidar quando o paciente começa a oferecer favores ou presentes?": """
    <div class="resposta-humanizada">
        <h3>Analise a função do ato.</h3>
        <p>É gratidão? É sedução? É tentativa de compra? Recuse favores que gerem dívida simbólica ("posso consertar seu carro"). Presentes pequenos podem ser aceitos se a recusa for mais danosa, mas sempre analise o significado clínico.</p>
    </div>
    """,

    "É ético manter contato com pacientes nas redes sociais?": """
    <div class="resposta-humanizada">
        <h3>Perfil Profissional: Sim. Perfil Pessoal: Evite.</h3>
        <p>Seguir o paciente de volta no seu perfil íntimo expõe sua privacidade e quebra o enquadre. Mantenha as interações restritas ao campo profissional.</p>
    </div>
    """,

    "O que fazer quando o psicólogo cruza socialmente com o paciente?": """
    <div class="resposta-humanizada">
        <h3>Discrição total.</h3>
        <p>Não tome a iniciativa de cumprimentar efusivamente. Espere o paciente. Se ele não falar, respeite. Se falar, seja breve e cordial, sem entrar em temas terapêuticos.</p>
    </div>
    """,

    "É possível uma relação terapêutica ética após uma relação prévia?": """
    <div class="resposta-humanizada">
        <h3>Muito difícil e arriscado.</h3>
        <p>Se já houve intimidade, romance ou conflito, a imagem que o paciente tem de você já está formada e dificilmente permitirá a projeção necessária para a terapia.</p>
    </div>
    """,

    "Como agir quando o paciente demonstra interesse afetivo ou sexual?": """
    <div class="resposta-humanizada">
        <h3>Manejo clínico rigoroso.</h3>
        <p>Não corresponda, mas acolha como material de trabalho (transferência erótica). Ajude o paciente a entender o que esse desejo representa na terapia. Se ficar insustentável ou houver assédio, o encaminhamento é necessário.</p>
    </div>
    """,

    "O que configura exploração da relação terapêutica?": """
    <div class="resposta-humanizada">
        <h3>Usar o paciente para benefício próprio.</h3>
        <p>Ex: Pedir votos políticos, vender produtos (Tupperware/Hinode), pedir emprego para parentes ou usar a influência psicológica para obter vantagens sexuais (infração gravíssima).</p>
    </div>
    """,

    "É ético atender familiares de ex-pacientes?": """
    <div class="resposta-humanizada">
        <h3>Zona de risco.</h3>
        <p>Se o atendimento anterior foi recente ou envolveu dinâmicas familiares intensas, evite. O sigilo do ex-paciente pode ser comprometido pelo que o novo paciente trouxer.</p>
    </div>
    """,

    "Como identificar conflitos de interesse sutis na prática clínica?": """
    <div class="resposta-humanizada">
        <h3>Sinais de alerta:</h3>
        <ul>
            <li>Você evita tocar em certos assuntos por medo de perder o paciente (financeiro).</li>
            <li>Você se sente "devendo" algo ao paciente.</li>
            <li>Você torce excessivamente por um desfecho na vida dele.</li>
        </ul>
    </div>
    """,

    # ---------------------------------------------------------
    # 💬 COMUNICAÇÃO, POSTURA E MANEJO
    # ---------------------------------------------------------
    "Existe limite ético para a autorrevelação do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Sim: O benefício do paciente.</h3>
        <p>Falar de si só é válido se tiver objetivo terapêutico claro. Desabafar seus problemas, falar de suas conquistas por vaidade ou comparar dores ("eu também sofri isso") geralmente desloca o foco e é falha técnica.</p>
    </div>
    """,

    "Quando o silêncio pode ser eticamente problemático?": """
    <div class="resposta-humanizada">
        <h3>Quando é negligência ou punição.</h3>
        <p>O silêncio técnico é ferramenta. O silêncio porque você não sabe o que fazer, está com sono ou irritado com o paciente, é abandono disfarçado.</p>
    </div>
    """,

    "Como manejar discordâncias de valores sem impor crenças pessoais?": """
    <div class="resposta-humanizada">
        <h3>Validação e foco no sofrimento.</h3>
        <p>Você não precisa concordar (ex: política, religião), precisa entender como aquilo funciona para o sujeito. Se o valor do paciente fere Direitos Humanos (ex: racismo), o psicólogo deve se posicionar conforme os Princípios Fundamentais, mas de forma clínica, não agressiva.</p>
    </div>
    """,

    "É ético confrontar diretamente o paciente?": """
    <div class="resposta-humanizada">
        <h3>Sim, a confrontação técnica é válida.</h3>
        <p>Confrontar contradições do discurso é trabalho. Ser agressivo, irônico ou moralista não é confrontação, é desrespeito.</p>
    </div>
    """,

    "Como agir quando o paciente questiona a competência do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Não se defenda atacando.</h3>
        <p>Acolha a dúvida. Pergunte o que gerou essa sensação. Pode ser uma resistência do paciente ou uma falha real sua. Analise com humildade e, se necessário, supervisione.</p>
    </div>
    """,

    "O que caracteriza uma postura clínica respeitosa?": """
    <div class="resposta-humanizada">
        <h3>Pontualidade, escuta ativa e ambiente adequado.</h3>
        <p>Respeito vai além de "ser educado". É não desmarcar em cima da hora sem motivo, não atender mexendo no celular e garantir que ninguém ouça a sessão.</p>
    </div>
    """,

    "É ético prolongar um processo terapêutico sem ganhos claros?": """
    <div class="resposta-humanizada">
        <h3>Não. É vedado (Art. 2º 'n').</h3>
        <p>Se a terapia estagnou, discuta isso com o paciente. Proponha novos objetivos, dê alta ou encaminhe.</p>
    </div>
    """,

    "Quando a frustração do psicólogo interfere eticamente na clínica?": """
    <div class="resposta-humanizada">
        <h3>Quando vira atuação (acting-out).</h3>
        <p>Se você começa a ser ríspido, esquecer sessões ou "desistir" internamente do paciente por frustração, você está prejudicando o cuidado. Busque supervisão urgente.</p>
    </div>
    """,

    "O que fazer quando o psicólogo percebe antipatia pelo paciente?": """
    <div class="resposta-humanizada">
        <h3>Supervisão e Análise Pessoal.</h3>
        <p>Se o sentimento impedir a empatia e o acolhimento, é mais ético encaminhar do que atender "mal".</p>
    </div>
    """,

    "Como manejar erros cometidos durante o processo terapêutico?": """
    <div class="resposta-humanizada">
        <h3>Transparência e reparação.</h3>
        <p>Se errou (esqueceu sessão, falou algo inadequado), reconheça, peça desculpas e analise o impacto disso na relação. A onipotência de "não errar" é prejudicial.</p>
    </div>
    """,

    # ---------------------------------------------------------
    # 🧠 AUTONOMIA, RESPONSABILIDADE E CUIDADO
    # ---------------------------------------------------------
    "Como respeitar a autonomia do paciente em escolhas autodestrutivas?": """
    <div class="resposta-humanizada">
        <h3>O limite é a capacidade civil e o risco de vida.</h3>
        <p>Se o paciente é capaz e não há risco iminente de morte, ele tem direito a fazer escolhas ruins (ex: gastar todo dinheiro, manter relação tóxica). O psicólogo aponta, mas não proíbe.</p>
    </div>
    """,

    "Quando o cuidado justifica uma intervenção mais diretiva?": """
    <div class="resposta-humanizada">
        <h3>Em crises e perda de crítica.</h3>
        <p>Surto psicótico, risco de suicídio, abuso de substâncias com risco vital. Nesses casos, a proteção à vida se sobrepõe temporariamente à autonomia.</p>
    </div>
    """,

    "É ético continuar atendendo um paciente que não deseja mudanças?": """
    <div class="resposta-humanizada">
        <h3>Depende do contrato.</h3>
        <p>Às vezes a demanda é apenas suporte/manutenção, não mudança radical. Se isso for acordado, ok. Se o psicólogo sente que não há função terapêutica, deve discutir a alta.</p>
    </div>
    """,

    "Como lidar com demandas que contrariam princípios pessoais do psicólogo?": """
    <div class="resposta-humanizada">
        <h3>Encaminhamento responsável.</h3>
        <p>Se você não consegue acolher (ex: questões de aborto, religião, identidade de gênero) por convicção pessoal, reconheça sua limitação e encaminhe para alguém que acolha sem julgamento.</p>
    </div>
    """,

    "O que caracteriza negligência ética na clínica?": """
    <div class="resposta-humanizada">
        <h3>Omissão de cuidado.</h3>
        <p>Ignorar risco de suicídio, não fazer prontuário, faltar sem avisar, deixar o paciente sem respaldo em crises.</p>
    </div>
    """,

    "Quando a desistência do atendimento é eticamente justificável?": """
    <div class="resposta-humanizada">
        <h3>Quando há ameaça/violência ou limite técnico.</h3>
        <p>O psicólogo não é obrigado a atender quem o agride, ameaça ou assedia. Nesses casos, encerre o contrato garantindo apenas a segurança do encaminhamento.</p>
    </div>
    """,

    "Como lidar com faltas e inadimplência sem violar a ética?": """
    <div class="resposta-humanizada">
        <h3>Contrato claro desde o início.</h3>
        <p>Cobrar sessões faltadas é ético se foi combinado. Cobrar dívidas deve ser feito de forma respeitosa, sem expor o paciente a vexame (Art. 4º).</p>
    </div>
    """,

    "O que é responsabilidade ética na clínica além do Código?": """
    <div class="resposta-humanizada">
        <h3>Compromisso social e Direitos Humanos.</h3>
        <p>É combater preconceitos, entender o contexto social do sofrimento e não patologizar a pobreza ou a diversidade.</p>
    </div>
    """,

    "É ético atender pacientes em sofrimento intenso sem suporte de rede?": """
    <div class="resposta-humanizada">
        <h3>É desafiador, mas ético.</h3>
        <p>O psicólogo deve ajudar a construir essa rede (CAPS, Assistência Social, grupos). Não abandone o paciente por ser um "caso difícil", mas não tente ser a única rede dele.</p>
    </div>
    """,

    "Como a ética se manifesta nas pequenas decisões cotidianas da clínica?": """
    <div class="resposta-humanizada">
        <h3>Nos detalhes.</h3>
        <p>Está em responder uma mensagem com cuidado, em ter uma sala com isolamento acústico real, em guardar o prontuário na chave, em estudar o caso antes da sessão.</p>
    </div>
    """
}

# Lista atualizada de botões (Mix de temas para atrair o usuário)
QUICK_QUESTIONS = [
    "Até onde vai o sigilo em caso de crime?",
    "O que fazer se o juiz pedir o prontuário?",
    "Posso atender familiares de ex-pacientes?",
    "Eu sou obrigada fazer anotações?",
    "Posso atender de graça?",
    "É ético atender amigos?",
    "Como lidar com inadimplência?",
    "Posso aceitar presentes?",
    "Paciente pediu para não registrar no prontuário"
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
# BUSCA E LÓGICA
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
# ROTAS
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
            
            # B) Tenta Match Parcial (Lógica de aproximação)
            else:
                found_partial = False
                for key, val in RESPOSTAS_PRONTAS.items():
                    # Se houver muitas palavras em comum, assume que é a mesma pergunta
                    key_words = set(key.lower().replace("?","").split())
                    q_words = set(q.lower().replace("?","").split())
                    
                    # Interseção de palavras significativas
                    common = key_words.intersection(q_words)
                    
                    # Se coincidir mais de 60% das palavras da chave
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
                            <div class="alert-box tip">💡 Tente usar os botões de sugestão para respostas mais completas.</div>
                        </div>
                        """
                    else:
                        answer = """
                        <div class="resposta-humanizada">
                            <h3>🤔 Dúvida não encontrada.</h3>
                            <div class="alert-box warning">
                                Não encontrei uma resposta específica no meu banco de dados atual.
                            </div>
                            <p>Tente reformular ou clique em um dos botões abaixo.</p>
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
