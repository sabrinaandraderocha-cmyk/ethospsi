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
app.config["SECRET_KEY"] = "dev-ethospsi-secret-final-v3"

DATA_DIR = os.path.abspath("./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ethospsi.sqlite3")

# Ajuste para busca no texto
CHUNK_CHARS = 800  
CHUNK_OVERLAP = 100

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)

# =====================================================
# RESPOSTAS PRONTAS (CURADORIA CLÍNICA EXPANDIDA)
# =====================================================
RESPOSTAS_PRONTAS = {
    # --- RELAÇÕES E VÍNCULOS ---
    "Posso atender familiares de ex-pacientes?": """
    <div class="resposta-humanizada">
        <h3>Pode atender, mas com muitas ressalvas éticas.</h3>
        <p>Na prática clínica, <strong>não é recomendado</strong> atender familiares próximos (pais, filhos, irmãos, cônjuge). Mesmo que não seja explicitamente "proibido", fere o princípio da neutralidade e do sigilo.</p>
        <div class="alert-box warning">
            <strong>Risco:</strong> Confusão de papéis, quebra involuntária de sigilo e prejuízo ao vínculo terapêutico. Se puder, encaminhe.
        </div>
    </div>
    """,

    "Posso ir a eventos sociais em que meu paciente esta?": """
    <div class="resposta-humanizada">
        <h3>Zona de Cuidado: Evite Relações Duplas.</h3>
        <p>Se for um evento grande (show, palestra), tudo bem. Se for íntimo (aniversário, jantar na casa de amigos em comum), sua presença pode inibir o paciente ou configurar uma relação pessoal que interfere na profissional.</p>
        <p><strong>Dica:</strong> Se o encontro for inevitável, mantenha postura discreta e profissional. Não aja como "amiga" íntima.</p>
    </div>
    """,

    "Devo cumprimentar meu paciente na rua?": """
    <div class="resposta-humanizada">
        <h3>Regra de Ouro: Espere o paciente reagir.</h3>
        <p>O sigilo sobre a existência do tratamento é direito dele. Se você cumprimentar primeiro, pode expor para quem estiver com ele que vocês se conhecem (e de onde).</p>
        <div class="alert-box tip">
            💡 <strong>Combine antes:</strong> "Se nos encontrarmos na rua, vou esperar você me dar oi para proteger sua privacidade, ok?"
        </div>
    </div>
    """,

    "Posso aceitar presentes de um paciente?": """
    <div class="resposta-humanizada">
        <h3>Depende do significado e do valor.</h3>
        <p>O Código de Ética (Art. 2º, 'o') veda receber vantagens além dos honorários. Porém, na clínica, pequenos presentes simbólicos (um desenho, um bombom) podem fazer parte do vínculo.</p>
        <p><strong>Analise:</strong> É uma tentativa de compra/sedução? É algo caro? Se for valioso, devolva explicando a ética. Se for simbólico, pode aceitar como manejo clínico.</p>
    </div>
    """,
    
    "Posso contar sobre a minha vida para o paciente?": """
    <div class="resposta-humanizada">
        <h3>Cuidado com a Auto-revelação (Self-disclosure).</h3>
        <p>A terapia é sobre o paciente, não sobre você. Falar da sua vida só é válido se tiver um <strong>objetivo terapêutico claro</strong> para ajudar aquele paciente naquele momento.</p>
        <p>Se for para desabafar ou "ficar amigo", é erro técnico e ético.</p>
    </div>
    """,

    # --- PRONTUÁRIOS E DOCUMENTOS ---
    "Eu sou obrigada fazer anotações?": """
    <div class="resposta-humanizada">
        <h3>Sim, é obrigatório.</h3>
        <p>Manter prontuário não é opcional. É dever do psicólogo (Resolução CFP 01/2009) para garantir a continuidade do serviço e a defesa técnica em caso de processos.</p>
        <p><strong>O que anotar?</strong> Evolução, datas, procedimentos e encaminhamentos. Não precisa ser a transcrição da fala, mas a síntese técnica.</p>
    </div>
    """,

    "O que é obrigatório eu anotar no prontuário?": """
    <div class="resposta-humanizada">
        <h3>Itens Obrigatórios (Resolução CFP 01/2009):</h3>
        <ul>
            <li>Identificação do usuário;</li>
            <li>Avaliação de demanda e definição de objetivos;</li>
            <li>Registro da evolução (datas e síntese dos atendimentos);</li>
            <li>Procedimentos técnico-científicos adotados;</li>
            <li>Encaminhamentos ou encerramento.</li>
        </ul>
    </div>
    """,

    "Posso usar prontuários de forma digital?": """
    <div class="resposta-humanizada">
        <h3>Sim, com segurança garantida.</h3>
        <p>Você pode abolir o papel, desde que o sistema garanta:</p>
        <ul>
            <li><strong>Confidencialidade:</strong> Senha forte e criptografia.</li>
            <li><strong>Autenticidade:</strong> De preferência com Assinatura Digital (e-CPF/ICP-Brasil).</li>
            <li><strong>Permanência:</strong> Backup seguro por 5 anos.</li>
        </ul>
        <div class="alert-box warning">Nota simples no celular ou Word sem senha não servem como prontuário seguro.</div>
    </div>
    """,

    "Como devo guardar prontuários antigos?": """
    <div class="resposta-humanizada">
        <h3>Prazo Mínimo: 5 Anos.</h3>
        <p>Você deve guardar os documentos por no mínimo 5 anos, mantendo o sigilo absoluto (arquivo trancado ou digital criptografado).</p>
    </div>
    """,

    "O que fazer se o juiz pedir o prontuário?": """
    <div class="resposta-humanizada">
        <h3>Não entregue tudo automaticamente!</h3>
        <p>O sigilo protege o paciente. Se intimada:</p>
        <ol>
            <li>Tente responder via <strong>Relatório/Laudo</strong> respondendo apenas aos quesitos do juiz.</li>
            <li>Se obrigada a entregar o prontuário bruto, lacre-o e peça <strong>Segredo de Justiça</strong>.</li>
        </ol>
        <p><em>Dica: Consulte a COF do seu CRP com o ofício em mãos.</em></p>
    </div>
    """,

    # --- SIGILO E FAMÍLIA ---
    "Ao dar devolutiva para os pais apos atendimento devo contar tudo que a criança disse?": """
    <div class="resposta-humanizada">
        <h3>Não! A criança também tem direito ao sigilo.</h3>
        <p>O Art. 13 do Código de Ética é claro: aos responsáveis, comunica-se apenas o <strong>estritamente essencial</strong> para promover medidas em benefício da criança.</p>
        <p><strong>O que falar?</strong> Riscos, orientações de manejo, dinâmicas gerais. Não conte segredos íntimos que não ofereçam risco, senão você quebra a confiança da criança em você.</p>
    </div>
    """,

    "O que posso compartilhar em uma supervisão?": """
    <div class="resposta-humanizada">
        <h3>Apenas o caso clínico, nunca a identidade.</h3>
        <p>A supervisão é fundamental para a qualidade (Art. 1º 'c'). Você pode e deve discutir o manejo, mas deve <strong>anonimizar</strong> o paciente.</p>
        <p>Não diga nome, local de trabalho específico ou detalhes que permitam ao supervisor identificar quem é a pessoa socialmente.</p>
    </div>
    """,

    "Preciso ter um contato emergencial para todo paciente?": """
    <div class="resposta-humanizada">
        <h3>Sim, é uma medida de segurança recomendada.</h3>
        <p>Especialmente em casos com risco de suicídio, surto ou vulnerabilidade. Tenha o contato anotado e combine com o paciente em que situações extremas aquele contato será acionado (quebra de sigilo por risco de vida, Art. 10).</p>
    </div>
    """,

    # --- QUESTÕES ÉTICAS E SOCIAIS ---
    "Posso atender de graça?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas cuide do enquadre.</h3>
        <p>O atendimento pro bono (voluntário) é permitido e nobre. O que o Código veda é usar o preço baixo como propaganda ("Sessão a R$ 10,00!") para captar clientela de forma desleal.</p>
        <p><strong>Dica:</strong> Se for atender de graça, mantenha o mesmo rigor, horário e comprometimento do atendimento pago. O contrato terapêutico deve ser claro.</p>
    </div>
    """,

    "Posso influenciar na orientação sexual do meu paciente?": """
    <div class="resposta-humanizada">
        <h3>JAMAIS. Isso é infração ética grave.</h3>
        <p><strong>Art. 2º 'b' do Código de Ética:</strong> É vedado ao psicólogo induzir a convicções de orientação sexual.</p>
        <p>Além disso, a Resolução 01/99 proíbe qualquer tipo de "terapia de conversão" ou patologização da homossexualidade. O papel da psicologia é o acolhimento, nunca o julgamento ou tentativa de mudança da orientação.</p>
    </div>
    """,

    "Existe psicologia evangélica?": """
    <div class="resposta-humanizada">
        <h3>Não existe "Psicologia Cristã" como ciência.</h3>
        <p>A Psicologia é uma ciência laica. Você pode ser cristã/evangélica, mas sua prática técnica não pode ser religiosa.</p>
        <p><strong>Limites:</strong></p>
        <ul>
            <li>Você deve respeitar a fé do paciente.</li>
            <li>Você <strong>não pode</strong> pregar, orar durante a sessão (como técnica) ou tentar converter o paciente (Art. 2º 'b').</li>
        </ul>
    </div>
    """,

    "É proíbido falar sobre religião nas sessões?": """
    <div class="resposta-humanizada">
        <h3>Falar SOBRE religião é permitido e necessário.</h3>
        <p>Se a fé é importante para o paciente, ela faz parte da subjetividade dele e deve ser acolhida.</p>
        <p><strong>O que é proibido:</strong> O psicólogo impor suas crenças, usar a sessão para catequizar ou julgar a fé do paciente com base em dogmas pessoais.</p>
    </div>
    """,
    
    "Posso divulgar o valor da sessão no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Pode informar, mas não prometer desconto.</h3>
        <p>O preço não pode ser usado como chamariz promocional ("Promoção de Black Friday!"). Mas ter uma tabela de valores acessível ou responder quanto custa é transparência permitida.</p>
    </div>
    """,
    
    "Preciso de contrato para terapia online?": """
    <div class="resposta-humanizada">
        <h3>Sim, é fundamental.</h3>
        <p>Estabeleça por escrito: sigilo, plataforma usada, o que acontece se a internet cair, política de faltas e contato de emergência.</p>
    </div>
    """
}

# Lista atualizada de botões para aparecer na tela
QUICK_QUESTIONS = [
    "Posso atender familiares de ex-pacientes?",
    "Eu sou obrigada fazer anotações?",
    "Posso atender de graça?",
    "Ao dar devolutiva para os pais devo contar tudo?",
    "Posso aceitar presentes de um paciente?",
    "Posso influenciar na orientação sexual?",
    "Existe psicologia evangélica?",
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
c) Prestar serviços psicológicos de qualidade, utilizando princípios fundamentados na ciência psicológica, na ética e na legislação.
j) Ter, para com o trabalho dos psicólogos e de outros profissionais, respeito, consideração e solidariedade.
Art. 2º Ao psicólogo é vedado:
a) Praticar ou ser conivente com quaisquer atos que caracterizem negligência, discriminação, exploração, violência, crueldade ou opressão.
b) Induzir a convicções políticas, filosóficas, morais, ideológicas, religiosas, de orientação sexual ou a qualquer tipo de preconceito.
f) Prestar serviços ou vincular o título de psicólogo a serviços de atendimento psicológico cujos procedimentos, técnicas e meios não estejam regulamentados ou reconhecidos pela profissão.
j) Estabelecer com a pessoa atendida, familiar ou terceiro, relação que possa interferir negativamente nos objetivos do serviço prestado.
o) Receber, pagar remuneração ou porcentagem por encaminhamento de serviços.
q) Realizar diagnósticos, divulgar procedimentos ou apresentar resultados em meios de comunicação de forma a expor pessoas.
SIGILO PROFISSIONAL
Art. 9º - É dever do psicólogo respeitar o sigilo profissional a fim de proteger, por meio da confidencialidade, a intimidade das pessoas.
Art. 13 - No atendimento à criança, ao adolescente ou ao interdito, deve ser comunicado aos responsáveis o estritamente essencial para se promoverem medidas em seu benefício.
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
            
            # B) Tenta Match Parcial (Se o usuário digitar algo parecido com as perguntas prontas)
            else:
                found_partial = False
                for key, val in RESPOSTAS_PRONTAS.items():
                    # Se 80% das palavras da chave estiverem na pergunta do usuário (lógica simples)
                    key_words = set(key.lower().replace("?","").split())
                    q_words = set(q.lower().replace("?","").split())
                    if len(key_words.intersection(q_words)) >= len(key_words) * 0.7:
                         answer = val
                         found_partial = True
                         break
                
                # C) Busca Genérica no Texto
                if not found_partial:
                    hits = simple_search(q)
                    if hits:
                        html_hits = "".join([f"<div class='ref-card source-cfp'><div class='ref-body'>...{h}...</div></div>" for h in hits])
                        answer = f"""
                        <div class="resposta-humanizada">
                            <h3>Resultados da Busca</h3>
                            <p>Não encontrei uma resposta exata para sua dúvida, mas veja o que o Código diz sobre temas relacionados:</p>
                            {html_hits}
                            <div class="alert-box tip">💡 Tente simplificar a pergunta ou consulte os botões de sugestão.</div>
                        </div>
                        """
                    else:
                        answer = """
                        <div class="resposta-humanizada">
                            <h3>🤔 Dúvida complexa...</h3>
                            <div class="alert-box warning">
                                Não encontrei uma resposta específica no meu banco de dados atual.
                            </div>
                            <p>Tente reformular usando termos como: <strong>"sigilo"</strong>, <strong>"prontuário"</strong>, <strong>"família"</strong> ou <strong>"religião"</strong>.</p>
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
