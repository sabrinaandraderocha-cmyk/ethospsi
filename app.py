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
app.config["SECRET_KEY"] = "dev-ethospsi-secret-final"

DATA_DIR = os.path.abspath("./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ethospsi.sqlite3")

# Ajuste para busca no texto
CHUNK_CHARS = 800  
CHUNK_OVERLAP = 100

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)

# =====================================================
# RESPOSTAS PRONTAS (CURADORIA CLÍNICA)
# =====================================================
RESPOSTAS_PRONTAS = {
    "Posso atender familiares de ex-pacientes?": """
    <div class="resposta-humanizada">
        <h3>Pode atender, mas com muitas ressalvas éticas.</h3>
        <p>Na prática clínica, <strong>não é recomendado</strong> atender familiares próximos (pais, filhos, irmãos, cônjuge), mesmo que o Código de Ética não proíba explicitamente com essas palavras.</p>
        
        <h4>🧠 Por que evitar?</h4>
        <ul>
            <li><strong>Neutralidade:</strong> É difícil manter a escuta isenta conhecendo a outra parte.</li>
            <li><strong>Sigilo:</strong> Risco de vazamento de informações (mesmo sem querer) ou confusão sobre quem disse o quê.</li>
            <li><strong>Vínculo:</strong> Pode gerar conflitos de papéis e prejudicar o processo terapêutico de ambos.</li>
        </ul>

        <div class="alert-box warning">
            <strong>Regra de Ouro:</strong> Se houver qualquer risco à sua neutralidade ou ao sigilo, o correto é <strong>não atender</strong> e encaminhar para um colega.
        </div>
        
        <p><strong>Dica Prática:</strong> Acolha a demanda e explique: <em>"Para garantir a qualidade do seu atendimento e o sigilo ético, o ideal é que você faça terapia com um profissional que não tenha vínculo com seu familiar. Posso te indicar excelentes colegas."</em></p>
    </div>
    """,

    "Como devo guardar prontuários antigos?": """
    <div class="resposta-humanizada">
        <h3>Guarda de Documentos (Resolução CFP 01/2009)</h3>
        <p>O prazo mínimo de guarda é de <strong>5 anos</strong>. O sigilo deve ser mantido rigorosamente durante todo esse tempo.</p>
        
        <h4>🔒 Como guardar com segurança?</h4>
        <ul>
            <li><strong>Físicos:</strong> Em armários com chave, em sala com acesso restrito.</li>
            <li><strong>Digitais:</strong> Em nuvem criptografada, HD externo com senha ou softwares específicos para psicólogos (prontuários eletrônicos).</li>
        </ul>
        
        <p><strong>Descarte:</strong> Após 5 anos, os documentos devem ser destruídos de forma que as informações não possam ser recuperadas (picotadora de papel ou exclusão segura digital).</p>
    </div>
    """,
    
    "Posso divulgar o valor da sessão no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas não como propaganda promocional.</h3>
        <p>O Código de Ética (Art. 20) proíbe utilizar o preço como forma de <strong>propaganda</strong> para captar clientes (ex: "Sessão com desconto", "Black Friday da Terapia").</p>
        
        <p>No entanto, informar o valor de forma clara e objetiva para quem pergunta, ou ter uma tabela de honorários disponível (ex: no Linktree ou Destaques), não é infração. O foco da divulgação deve ser sempre a qualidade do serviço, não o "preço baixo".</p>
    </div>
    """,

    "O que fazer se o juiz pedir o prontuário?": """
    <div class="resposta-humanizada">
        <h3>Cuidado: O Sigilo ainda existe!</h3>
        <p>Quando intimado por um juiz, você não deve enviar o prontuário inteiro automaticamente, a menos que seja explicitamente ordenado após justificativa.</p>
        <ul>
            <li><strong>Relatório Específico:</strong> O ideal é elaborar um documento respondendo estritamente aos quesitos do juiz, sem expor a intimidade desnecessária do paciente.</li>
            <li><strong>Segredo de Justiça:</strong> Se for obrigado a entregar documentos brutos, solicite que eles tramitem em Segredo de Justiça e lacre o envelope indicando "Confidencial - Acesso restrito ao Perito/Juiz".</li>
        </ul>
        <p><em>Dica: Em caso de dúvida, leve o ofício judicial à COF do seu CRP para orientação específica.</em></p>
    </div>
    """,
    
    "Preciso de contrato para terapia online?": """
    <div class="resposta-humanizada">
        <h3>Sim, é fundamental (e protege você).</h3>
        <p>Embora não seja "obrigatório" por lei ter um papel assinado, o contrato terapêutico estabelece as regras do jogo e evita processos éticos e mal-entendidos.</p>
        
        <h4>📝 O que deve constar?</h4>
        <ul>
            <li><strong>Sigilo e Tecnologia:</strong> Quais apps serão usados e os riscos da internet.</li>
            <li><strong>Faltas e Pagamentos:</strong> Política de cancelamento (ex: cobrar se não avisar com 24h).</li>
            <li><strong>Contato fora da sessão:</strong> Se você responde WhatsApp ou não.</li>
            <li><strong>Emergências:</strong> Contato de um familiar para casos de risco de vida.</li>
        </ul>
    </div>
    """
}

# =====================================================
# DADOS BASE (PARA BUSCA GENÉRICA)
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
j) Estabelecer com a pessoa atendida, familiar ou terceiro, relação que possa interferir negativamente nos objetivos do serviço prestado.
q) Realizar diagnósticos, divulgar procedimentos ou apresentar resultados em meios de comunicação de forma a expor pessoas.
SIGILO PROFISSIONAL
Art. 9º - É dever do psicólogo respeitar o sigilo profissional a fim de proteger, por meio da confidencialidade, a intimidade das pessoas.
Art. 10 - Em conflito, o psicólogo poderá decidir pela quebra de sigilo baseando sua decisão na busca do menor prejuízo.
Art. 20 - O psicólogo, ao promover publicamente seus serviços:
d) Não utilizará o preço do serviço como forma de propaganda.
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
    # Salva no histórico
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
# BUSCA
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
    keywords = [t for t in terms if len(t) > 3] # Ignora palavras curtas
    
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
        # 1. Resetar Base (Vindo do Admin)
        if "load_bases" in request.form:
            clear_documents()
            index_content("Código de Ética", TEXTO_CODIGO_ETICA)
            flash("Bases de conhecimento recarregadas com sucesso!", "success")
            return redirect(url_for('home'))

        # 2. Processar Pergunta
        q = request.form.get("q", "").strip()
        
        if q:
            # A) Tenta Match Exato (Botões)
            if q in RESPOSTAS_PRONTAS:
                answer = RESPOSTAS_PRONTAS[q]
            
            # B) Se não, faz a busca genérica
            else:
                hits = simple_search(q)
                if hits:
                    html_hits = "".join([f"<div class='ref-card source-cfp'><div class='ref-body'>...{h}...</div></div>" for h in hits])
                    answer = f"""
                    <div class="resposta-humanizada">
                        <h3>Resultados Encontrados</h3>
                        <p>Não tenho uma resposta pronta para essa pergunta específica, mas encontrei estes trechos no Código:</p>
                        {html_hits}
                        <div class="alert-box tip">💡 Para casos complexos, consulte sempre a COF do seu CRP.</div>
                    </div>
                    """
                else:
                    answer = """
                    <div class="alert-box warning">
                        ⚠️ <strong>Não encontrei informações.</strong><br>
                        Tente usar palavras-chave como "sigilo", "registro", "família" ou use os botões de sugestão.
                    </div>
                    """
            
            save_history(q, answer)

    return render_template("home.html", 
                         app_name=APP_NAME, 
                         stats=stats(), 
                         history=get_history(50), 
                         answer=answer,
                         quick_questions=list(RESPOSTAS_PRONTAS.keys()))

@app.route("/admin")
def admin():
    return render_template("admin.html", stats=stats(), app_name=APP_NAME)

if __name__ == "__main__":
    init_db()
    if stats()["chunks"] == 0:
        index_content("Código de Ética", TEXTO_CODIGO_ETICA)
    app.run(debug=True, port=5000)