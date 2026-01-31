import os
import sqlite3
from datetime import datetime
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file
)

from docx import Document

# =====================================================
# CONFIG
# =====================================================
APP_NAME = "EthosPsi"
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-ethospsi-secret-final-v5")

DATA_DIR = os.path.abspath("./data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "ethospsi.sqlite3")

# Links oficiais (usados na página Recursos)
LINKS_OFICIAIS = {
    "codigo_etica_pdf_2025": "https://transparencia.cfp.org.br/wp-content/uploads/sites/29/2025/04/CodigoDeEtica_2025_Digital.pdf",
    "tabela_honorarios_cfp": "https://site.cfp.org.br/servicos/tabela-de-honorarios/",
    "tabela_honorarios_pdf_ate_julho_2025": "https://site.cfp.org.br/wp-content/uploads/2025/12/3699.1___ANEXO_REF_AO_OFICIO_N__009_20225___FENAPSI.pdf",
}

# =====================================================
# TEXTO BASE (para busca genérica)
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
# RESPOSTAS PRONTAS (curadoria)
# =====================================================
RESPOSTAS_PRONTAS = {
    "Posso atender familiares de ex-pacientes?": """
    <div class="resposta-humanizada">
      <h3>Pode, mas com muitas ressalvas éticas.</h3>
      <p>Na prática clínica, <strong>não é recomendado</strong> atender familiares próximos. Isso aumenta risco de relação dual, conflito de interesse e quebra involuntária de sigilo.</p>
      <div class="alert-box warning">
        <strong>Risco:</strong> confusão de papéis e prejuízo do vínculo terapêutico. Se puder, encaminhe.
      </div>
    </div>
    """,
    "Posso ir a eventos sociais em que meu paciente esta?": """
    <div class="resposta-humanizada">
      <h3>Zona de cuidado: evite relações duplas.</h3>
      <p>Eventos grandes tendem a ser menos problemáticos; eventos íntimos aumentam risco de confundir papéis e inibir o paciente.</p>
      <p><strong>Conduta prática:</strong> discrição, pouco contato e retomar o enquadre na sessão se for relevante.</p>
    </div>
    """,
    "Devo cumprimentar meu paciente na rua?": """
    <div class="resposta-humanizada">
      <h3>Regra de ouro: espere o paciente.</h3>
      <p>O sigilo sobre a existência do atendimento é direito do paciente. Cumprimentar primeiro pode expor vínculo.</p>
      <div class="alert-box tip">
        💡 <strong>Combine antes:</strong> “Se nos encontrarmos, vou esperar você cumprimentar para proteger sua privacidade, ok?”
      </div>
    </div>
    """,
    "Posso aceitar presentes de um paciente?": """
    <div class="resposta-humanizada">
      <h3>Depende do valor e do significado.</h3>
      <p>Presentes caros, frequentes ou com expectativa de retribuição são alerta. Presentes simbólicos podem acontecer, mas precisam ser avaliados pelo contexto e pelo manejo.</p>
      <div class="alert-box warning">
        <strong>Sinal de risco:</strong> tentativa de comprar atenção, sedução, controle ou quebra de limites.
      </div>
    </div>
    """,
    "Posso aceitar presentes?": """
    <div class="resposta-humanizada">
      <h3>Depende do contexto.</h3>
      <p>Presentes caros, frequentes ou com “cobrança” devem ser recusados. Presentes simbólicos podem ser avaliados clinicamente, com cautela.</p>
    </div>
    """,
    "Sou obrigada a fazer anotações?": """
    <div class="resposta-humanizada">
      <h3>Sim, registro é dever profissional.</h3>
      <p>Registre o essencial, de forma técnica e suficiente. Você não precisa escrever detalhes íntimos desnecessários.</p>
    </div>
    """,
    "O que é obrigatório eu anotar no prontuário?": """
    <div class="resposta-humanizada">
      <h3>O essencial: processo, evolução e conduta.</h3>
      <ul>
        <li>Identificação mínima necessária</li>
        <li>Demanda e objetivos</li>
        <li>Datas e síntese técnica da evolução</li>
        <li>Intervenções e combinados</li>
        <li>Encaminhamentos e encerramento</li>
      </ul>
    </div>
    """,
    "Paciente pediu para não registrar no prontuário": """
    <div class="resposta-humanizada">
      <h3>Explique que o registro técnico é dever.</h3>
      <p>Você pode combinar um registro mais sintético, sem detalhes íntimos, mas precisa registrar o essencial para continuidade do cuidado e proteção técnica.</p>
      <div class="alert-box tip">💡 “Vou registrar de forma técnica e sem detalhes desnecessários, para proteger você e o processo.”</div>
    </div>
    """,
    "O que fazer se o juiz pedir o prontuário?": """
    <div class="resposta-humanizada">
      <h3>Entregue o mínimo necessário.</h3>
      <ol>
        <li>Prefira responder por <strong>relatório</strong> limitado ao pedido.</li>
        <li>Se exigirem prontuário, solicite medidas de proteção (segredo de justiça) e reduza exposição.</li>
      </ol>
      <div class="alert-box tip">Em dúvida, procure orientação técnica do CRP (COF) com o ofício em mãos.</div>
    </div>
    """,
    "Preciso de contrato para terapia online?": """
    <div class="resposta-humanizada">
      <h3>Sim, recomendado.</h3>
      <p>Coloque por escrito: sigilo, plataforma, política de faltas, protocolo de queda de conexão, canal de contato e limites.</p>
    </div>
    """,
    "Posso cobrar multa por falta?": """
    <div class="resposta-humanizada">
      <h3>Pode, se estiver combinado previamente.</h3>
      <p>Coloque em contrato: prazo para desmarcação, remarcação e exceções. Mantenha tom respeitoso e foco no enquadre.</p>
    </div>
    """,
    "Como lidar com inadimplência?": """
    <div class="resposta-humanizada">
      <h3>Com dignidade e clareza.</h3>
      <p>Relembre o combinado, proponha renegociação e registre. Evite exposição. Se necessário, encerre com encaminhamento.</p>
    </div>
    """,
    "Posso cobrar PIX adiantado?": """
    <div class="resposta-humanizada">
      <h3>Pode, como regra de contrato.</h3>
      <p>Deixe claro: cancelamentos, remarcação e reembolso.</p>
    </div>
    """,
    "Existe cura gay?": """
    <div class="resposta-humanizada">
      <h3>Não existe “cura gay”.</h3>
      <p>Orientação sexual não é doença. O trabalho ético é acolher sofrimento, apoiar autonomia e enfrentar impactos de discriminação, sem objetivo de “mudar” orientação.</p>
    </div>
    """,
    "O que responder quando pedem terapia de reversão?": """
    <div class="resposta-humanizada">
      <h3>Responda com firmeza e cuidado.</h3>
      <p>Explique que não existe finalidade psicológica legítima para “reversão” de orientação sexual. Ofereça cuidado para sofrimento, culpa, ansiedade e conflitos, sem objetivo de mudança de orientação.</p>
      <div class="alert-box tip">💡 “Posso te ajudar com o sofrimento que você vive, mas não com a ideia de ‘mudar’ sua orientação sexual.”</div>
    </div>
    """,
    "Posso influenciar na orientação sexual do meu paciente?": """
    <div class="resposta-humanizada">
      <h3>Não. É vedado induzir convicções.</h3>
      <p>O cuidado ético prioriza acolhimento e autonomia, sem imposição moral, religiosa ou ideológica.</p>
    </div>
    """,
    "Existe psicologia evangélica?": """
    <div class="resposta-humanizada">
      <h3>A Psicologia é laica.</h3>
      <p>Você pode ter fé, mas não pode transformar a sessão em prática religiosa. A espiritualidade do paciente pode ser tema clínico, sem imposição.</p>
    </div>
    """,
    "É proíbido falar sobre religião nas sessões?": """
    <div class="resposta-humanizada">
      <h3>Não. Falar sobre fé pode ser necessário.</h3>
      <p>O que não pode é impor crenças, pregar, converter ou julgar com base em dogmas pessoais.</p>
    </div>
    """,
    "Posso seguir paciente no Instagram?": """
    <div class="resposta-humanizada">
      <h3>Em geral, não é recomendado.</h3>
      <p>Redes sociais aumentam risco de relação dual e exposição. O mais seguro é manter separação. Se houver motivo excepcional, combine limites e registre.</p>
    </div>
    """,
    "Posso responder mensagens fora do horário?": """
    <div class="resposta-humanizada">
      <h3>Defina limites de comunicação.</h3>
      <p>Combine horário, canal e finalidade (ex.: remarcação). Deixe claro que não é canal de urgência.</p>
    </div>
    """,
}

# =====================================================
# 100 DÚVIDAS ÉTICAS (BOTÕES)
# =====================================================
QUICK_QUESTIONS = [
    "Até onde vai o sigilo?",
    "Quando posso quebrar o sigilo?",
    "Posso confirmar para alguém que a pessoa é minha paciente?",
    "Posso falar do caso com meu cônjuge ou amigo?",
    "Como agir se um familiar pede informações do paciente?",
    "Como agir se o paciente pede segredo absoluto?",
    "Até onde vai o sigilo em caso de crime?",
    "Posso responder e-mail de familiar sobre o paciente?",
    "Posso discutir caso em grupo de WhatsApp profissional?",
    "O que fazer se eu quebrar o sigilo sem querer?",
    "Sou obrigada a fazer anotações?",
    "O que é obrigatório eu anotar no prontuário?",
    "Paciente pediu para não registrar no prontuário",
    "O paciente pode pedir cópia do prontuário?",
    "Como devo guardar prontuários antigos?",
    "Posso usar prontuários de forma digital?",
    "Posso usar IA para escrever prontuário?",
    "Por quanto tempo devo guardar prontuários?",
    "Posso negar um relatório solicitado?",
    "O que fazer se o juiz pedir o prontuário?",
    "Posso emitir declaração de comparecimento?",
    "Posso emitir laudo psicológico para processo?",
    "Posso emitir relatório para escola?",
    "Posso emitir relatório para empresa do paciente?",
    "Posso colocar CID em relatório?",
    "Posso assinar documento sem avaliação suficiente?",
    "Posso emitir relatório a pedido de familiar?",
    "Posso cobrar por relatório psicológico?",
    "Posso alterar um relatório após entregue?",
    "Posso recusar emitir laudo judicial?",
    "Posso atender amigos?",
    "Posso atender familiares?",
    "Posso atender familiares de ex-pacientes?",
    "Posso atender duas pessoas da mesma família individualmente?",
    "Posso atender casal e um dos parceiros individualmente?",
    "Posso atender alguém que eu já conheço socialmente?",
    "Posso atender paciente que trabalha comigo?",
    "Posso atender paciente que é meu chefe?",
    "Posso atender paciente que é meu professor?",
    "Posso manter amizade com paciente durante o tratamento?",
    "Devo cumprimentar meu paciente na rua?",
    "Posso ir a eventos sociais em que meu paciente esta?",
    "Posso seguir paciente no Instagram?",
    "Posso curtir posts do paciente?",
    "Posso ver stories do paciente?",
    "Posso bloquear paciente nas redes sociais?",
    "Posso pesquisar o paciente no Google?",
    "Posso responder mensagens fora do horário?",
    "Posso usar WhatsApp pessoal com pacientes?",
    "Posso ligar para o paciente fora do combinado?",
    "Preciso de contrato para terapia online?",
    "Como garantir sigilo no atendimento online?",
    "Posso atender online com paciente em outro estado?",
    "O que fazer quando a internet cai na sessão?",
    "Posso cobrar sessão cancelada por internet ruim?",
    "Posso atender por áudio no WhatsApp?",
    "Posso atender por mensagem (chat)?",
    "Posso atender paciente dirigindo?",
    "Posso atender paciente no trabalho dele?",
    "Posso gravar a sessão?",
    "Posso cobrar multa por falta?",
    "Como lidar com inadimplência?",
    "Posso cobrar PIX adiantado?",
    "Posso cobrar pacote de sessões?",
    "Posso atender de graça?",
    "Posso oferecer primeira sessão gratuita?",
    "Posso divulgar o valor da sessão no Instagram?",
    "Posso fazer sorteio de sessões?",
    "Posso receber comissão por encaminhamento?",
    "Posso fazer parceria com médico por indicação?",
    "Existe cura gay?",
    "O que responder quando pedem terapia de reversão?",
    "Posso influenciar na orientação sexual do meu paciente?",
    "Existe psicologia evangélica?",
    "É proíbido falar sobre religião nas sessões?",
    "Posso orar com o paciente na sessão?",
    "Posso recusar atendimento por conflito de valores?",
    "Posso recusar atendimento por falta de vaga?",
    "Quando devo encaminhar um paciente?",
    "Como encerrar terapia de forma ética?",
    "Como definir meu enquadre (horários, cancelamentos e atrasos)?",
    "Como criar um contrato terapêutico simples?",
    "Como organizar ficha de anamnese sem invadir demais?",
    "Posso atender em local público (cafeteria)?",
    "Como agir se o paciente pede desconto na sessão?",
    "Como lidar com faltas recorrentes sem culpabilizar?",
    "O que fazer se eu errar com o paciente?",
    "Posso confrontar o paciente?",
    "Posso dar conselhos diretos ao paciente?",
    "Como registrar sessão de forma sintética e segura?",
    "Como fazer devolutiva sem expor o paciente?",
    "Como lidar com pedido de “diagnóstico rápido”?",
    "Posso orientar medicação ao paciente?",
    "Como trabalhar em rede com psiquiatria sem quebrar sigilo?",
    "Como pedir autorização para falar com outro profissional?",
    "Posso atender adolescente sem os pais saberem?",
    "O que falar para os pais sobre a terapia do filho?",
    "Como agir em suspeita de violência (rede de proteção)?",
    "Como lidar com paciente que pede amizade nas redes?",
    "Como lidar com mensagens longas no WhatsApp?",
    "Como evitar dependência do paciente do meu contato?",
    "Como fazer encaminhamento sem abandonar?",
    "Como preparar alta e encerramento?",
    "Como lidar com pedido de relatório para INSS ou empresa?",
    "Como me proteger eticamente na publicidade profissional?",
    "Posso postar rotina e bastidores do consultório?",
    "Como citar casos clínicos sem identificar?",
    "Como escolher supervisão e manter sigilo do caso?",
    "Como definir política de reembolso?",
    "Como precificar sem culpa e sem exploração?",
]

# =====================================================
# SELOS (🟢 normativa | 🟡 zona de cuidado)
# - A ideia é simples:
#   • 🟢 quando tende a ter resposta mais "regra/conduta" e base normativa clara
#   • 🟡 quando depende mais de contexto (risco de relação dual, avaliação, manejo)
# - Você pode ajustar depois sem quebrar nada.
# =====================================================
QUESTION_SELOS = {
    # SIGILO / DOCUMENTOS (geralmente mais normativo)
    "Até onde vai o sigilo?": "normativa",
    "Quando posso quebrar o sigilo?": "normativa",
    "Posso confirmar para alguém que a pessoa é minha paciente?": "normativa",
    "Posso falar do caso com meu cônjuge ou amigo?": "normativa",
    "Até onde vai o sigilo em caso de crime?": "normativa",
    "Posso responder e-mail de familiar sobre o paciente?": "normativa",
    "Posso discutir caso em grupo de WhatsApp profissional?": "normativa",
    "O que fazer se eu quebrar o sigilo sem querer?": "zona",
    "Como agir se um familiar pede informações do paciente?": "normativa",
    "Como agir se o paciente pede segredo absoluto?": "zona",

    "Sou obrigada a fazer anotações?": "normativa",
    "O que é obrigatório eu anotar no prontuário?": "normativa",
    "Paciente pediu para não registrar no prontuário": "zona",
    "O paciente pode pedir cópia do prontuário?": "zona",
    "Como devo guardar prontuários antigos?": "normativa",
    "Posso usar prontuários de forma digital?": "normativa",
    "Posso usar IA para escrever prontuário?": "zona",
    "Por quanto tempo devo guardar prontuários?": "normativa",
    "Posso negar um relatório solicitado?": "zona",
    "O que fazer se o juiz pedir o prontuário?": "normativa",
    "Posso emitir declaração de comparecimento?": "normativa",
    "Posso emitir laudo psicológico para processo?": "zona",
    "Posso emitir relatório para escola?": "zona",
    "Posso emitir relatório para empresa do paciente?": "zona",
    "Posso colocar CID em relatório?": "zona",
    "Posso assinar documento sem avaliação suficiente?": "normativa",
    "Posso emitir relatório a pedido de familiar?": "zona",
    "Posso cobrar por relatório psicológico?": "zona",
    "Posso alterar um relatório após entregue?": "zona",
    "Posso recusar emitir laudo judicial?": "zona",

    # Relações duais / redes (normalmente zona de cuidado)
    "Posso atender amigos?": "zona",
    "Posso atender familiares?": "zona",
    "Posso atender familiares de ex-pacientes?": "zona",
    "Posso atender duas pessoas da mesma família individualmente?": "zona",
    "Posso atender casal e um dos parceiros individualmente?": "zona",
    "Posso atender alguém que eu já conheço socialmente?": "zona",
    "Posso atender paciente que trabalha comigo?": "zona",
    "Posso atender paciente que é meu chefe?": "zona",
    "Posso atender paciente que é meu professor?": "zona",
    "Posso manter amizade com paciente durante o tratamento?": "zona",
    "Devo cumprimentar meu paciente na rua?": "zona",
    "Posso ir a eventos sociais em que meu paciente esta?": "zona",
    "Posso seguir paciente no Instagram?": "zona",
    "Posso curtir posts do paciente?": "zona",
    "Posso ver stories do paciente?": "zona",
    "Posso bloquear paciente nas redes sociais?": "zona",
    "Posso pesquisar o paciente no Google?": "zona",
    "Posso responder mensagens fora do horário?": "zona",
    "Posso usar WhatsApp pessoal com pacientes?": "zona",
    "Posso ligar para o paciente fora do combinado?": "zona",

    # Online
    "Preciso de contrato para terapia online?": "normativa",
    "Como garantir sigilo no atendimento online?": "normativa",
    "Posso atender online com paciente em outro estado?": "zona",
    "O que fazer quando a internet cai na sessão?": "zona",
    "Posso cobrar sessão cancelada por internet ruim?": "zona",
    "Posso atender por áudio no WhatsApp?": "zona",
    "Posso atender por mensagem (chat)?": "zona",
    "Posso atender paciente dirigindo?": "zona",
    "Posso atender paciente no trabalho dele?": "zona",
    "Posso gravar a sessão?": "normativa",

    # Honorários (misto)
    "Posso cobrar multa por falta?": "normativa",
    "Como lidar com inadimplência?": "zona",
    "Posso cobrar PIX adiantado?": "normativa",
    "Posso cobrar pacote de sessões?": "zona",
    "Posso atender de graça?": "zona",
    "Posso oferecer primeira sessão gratuita?": "zona",
    "Posso divulgar o valor da sessão no Instagram?": "normativa",
    "Posso fazer sorteio de sessões?": "normativa",
    "Posso receber comissão por encaminhamento?": "normativa",
    "Posso fazer parceria com médico por indicação?": "zona",

    # Temas sensíveis e ética
    "Existe cura gay?": "normativa",
    "O que responder quando pedem terapia de reversão?": "normativa",
    "Posso influenciar na orientação sexual do meu paciente?": "normativa",
    "Existe psicologia evangélica?": "zona",
    "É proíbido falar sobre religião nas sessões?": "zona",
    "Posso orar com o paciente na sessão?": "zona",

    # Outros (se não estiverem mapeados, viram zona por padrão)
}

def selo_label(seal_code: str) -> str:
    if seal_code == "normativa":
        return "🟢 Resposta normativa"
    return "🟡 Zona de cuidado"

def build_quick_questions_with_seals():
    out = []
    for q in QUICK_QUESTIONS:
        seal_code = QUESTION_SELOS.get(q, "zona")
        out.append({
            "text": q,
            "seal": seal_code,
            "label": selo_label(seal_code),
        })
    return out

# =====================================================
# FALLBACK INTELIGENTE
# =====================================================
TEMA_DICAS = {
    "sigilo": [
        "Use o princípio do mínimo necessário.",
        "Evite confirmar vínculo terapêutico a terceiros.",
        "Em exceções, registre justificativa e medidas de proteção.",
    ],
    "prontuario": [
        "Registre o essencial: evolução, conduta, combinados e encaminhamentos.",
        "Evite detalhes íntimos desnecessários.",
        "Guarde com acesso restrito e backup seguro.",
    ],
    "redes": [
        "Evite seguir, curtir ou interagir com paciente em redes sociais.",
        "Limites digitais protegem o enquadre e o sigilo.",
        "Se necessário, alinhe em sessão de forma respeitosa.",
    ],
    "online": [
        "Combine plataforma, protocolo de queda e limites de comunicação.",
        "Oriente ambiente privado e uso de fone.",
        "Não transforme mensageria em plantão terapêutico.",
    ],
    "honorarios": [
        "Tenha política de faltas por escrito.",
        "Negociação deve preservar dignidade e enquadre.",
        "Use tabelas como referência, com realidade regional e custos.",
    ],
    "relacoes": [
        "Evite relação dual: amigos, familiares, vínculos próximos.",
        "Se inevitável, explicite limites e registre decisão.",
        "Em dúvida, encaminhe ou busque supervisão.",
    ],
    "geral": [
        "Se a decisão aumentar risco de exposição, recue e reoriente.",
        "Se houver dúvida, supervisão e orientação do CRP ajudam.",
        "Registre combinados importantes de forma técnica.",
    ],
}

def detectar_tema(pergunta: str) -> str:
    q = (pergunta or "").lower()
    if any(k in q for k in ["sigilo", "confirmar", "crime", "terceiro", "familia", "familiar"]):
        return "sigilo"
    if any(k in q for k in ["prontu", "registro", "anotar", "guardar", "relatório", "laudo", "declara"]):
        return "prontuario"
    if any(k in q for k in ["instagram", "rede", "stories", "curtir", "google", "bloquear"]):
        return "redes"
    if any(k in q for k in ["online", "internet", "whatsapp", "chat", "áudio", "audio"]):
        return "online"
    if any(k in q for k in ["honor", "cobrar", "multa", "inadimpl", "pix", "pacote", "desconto", "precificar"]):
        return "honorarios"
    if any(k in q for k in ["amigo", "famil", "casal", "professor", "chefe", "social"]):
        return "relacoes"
    return "geral"

def resposta_orientativa(pergunta: str) -> str:
    tema = detectar_tema(pergunta)
    dicas = TEMA_DICAS.get(tema, TEMA_DICAS["geral"])
    html_dicas = "".join([f"<li>{d}</li>" for d in dicas])

    return f"""
    <div class="resposta-humanizada">
      <h3>Orientação ética para esta dúvida</h3>
      <p><strong>Pergunta:</strong> {pergunta}</p>
      <p>Esta pergunta ainda não tem resposta específica cadastrada. Pelo tema (<strong>{tema}</strong>), estes princípios ajudam a decidir com segurança:</p>
      <ul>{html_dicas}</ul>
      <div class="alert-box tip">
        💡 Dica: use as abas <strong>Recursos</strong>, <strong>Políticas</strong> e <strong>Rede</strong> para textos prontos e roteiros.
      </div>
    </div>
    """

def garantir_respostas_para_botoes():
    for q in QUICK_QUESTIONS:
        if q not in RESPOSTAS_PRONTAS:
            RESPOSTAS_PRONTAS[q] = resposta_orientativa(q)

garantir_respostas_para_botoes()

# =====================================================
# DB
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
    conn.execute(
        "INSERT INTO qa_history (question, answer, created_at) VALUES (?,?,?)",
        (question, answer, datetime.now().strftime("%d/%m %H:%M"))
    )
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
    except Exception:
        return {"documents": 0, "chunks": 0, "history": 0}
    conn.close()
    return {"documents": d, "chunks": c, "history": h}

# =====================================================
# INDEX e BUSCA
# =====================================================
def index_content(title: str, text: str):
    chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 20]
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents (title, created_at) VALUES (?,?)",
        (title, datetime.now().strftime("%Y-%m-%d"))
    )
    doc_id = cur.lastrowid
    for c in chunks:
        cur.execute("INSERT INTO chunks (doc_id, chunk_text) VALUES (?,?)", (doc_id, c))
    conn.commit()
    conn.close()

def simple_search(query: str):
    conn = db()
    keywords = [t for t in (query or "").lower().split() if len(t) > 3]
    if not keywords:
        return []
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
# DOCX DOWNLOAD
# =====================================================
def _sanitize_filename(name: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ "
    cleaned = "".join([c if c in keep else "_" for c in (name or "")]).strip()
    return cleaned[:80] if cleaned else "documento"

def _make_docx_bytes(title: str, text: str) -> BytesIO:
    doc = Document()
    if title:
        doc.add_heading(title, level=1)

    lines = (text or "").replace("\r\n", "\n").split("\n")
    for line in lines:
        if line.strip() == "":
            doc.add_paragraph("")
        else:
            doc.add_paragraph(line)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

@app.route("/download-docx", methods=["POST"])
def download_docx():
    title = (request.form.get("doc_title") or "Documento").strip()
    text = request.form.get("doc_text") or ""
    filename = _sanitize_filename(request.form.get("doc_filename") or title)

    if not text.strip():
        flash("Nada para baixar. Gere o documento primeiro.", "success")
        return redirect(request.referrer or url_for("home"))

    bio = _make_docx_bytes(title=title, text=text)
    return send_file(
        bio,
        as_attachment=True,
        download_name=f"{filename}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# =====================================================
# ROTAS
# =====================================================
@app.route("/", methods=["GET", "POST"])
def home():
    answer = None

    if request.method == "POST":
        if "load_bases" in request.form:
            clear_documents()
            index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
            flash("Base atualizada com sucesso!", "success")
            return redirect(url_for("home"))

        q = (request.form.get("q") or "").strip()
        if q:
            if q in RESPOSTAS_PRONTAS:
                answer = RESPOSTAS_PRONTAS[q]
            else:
                hits = simple_search(q)
                if hits:
                    html_hits = "".join([
                        f"<div class='ref-card source-cfp'><div class='ref-body'>...{h}...</div></div>"
                        for h in hits
                    ])
                    answer = f"""
                    <div class="resposta-humanizada">
                      <h3>Resultados da Busca</h3>
                      <p>Não encontrei uma resposta exata, mas estes trechos podem ajudar:</p>
                      {html_hits}
                      <div class="alert-box tip">💡 Use as abas Políticas e Rede para textos prontos e roteiros.</div>
                    </div>
                    """
                else:
                    answer = resposta_orientativa(q)

            save_history(q, answer)

    return render_template(
        "home.html",
        app_name=APP_NAME,
        stats=stats(),
        history=get_history(50),
        answer=answer,
        quick_questions=build_quick_questions_with_seals()
    )

@app.route("/recursos")
def recursos():
    return render_template("resources.html", app_name=APP_NAME, links=LINKS_OFICIAIS)

@app.route("/contrato", methods=["GET", "POST"])
def contrato():
    contrato_txt = None
    if request.method == "POST":
        contrato_txt = gerar_contrato_texto(request.form)
    return render_template("contrato.html", app_name=APP_NAME, contrato_txt=contrato_txt)

@app.route("/honorarios", methods=["GET", "POST"])
def honorarios():
    resultado = None
    if request.method == "POST":
        resultado = calc_honorarios(request.form)
    return render_template("honorarios.html", app_name=APP_NAME, resultado=resultado, links=LINKS_OFICIAIS)

@app.route("/politicas", methods=["GET", "POST"])
def politicas():
    out = None
    if request.method == "POST":
        out = gerar_politica(request.form)
    return render_template("politicas.html", app_name=APP_NAME, out=out)

@app.route("/rede", methods=["GET", "POST"])
def rede():
    out = None
    if request.method == "POST":
        out = gerar_rede(request.form)
    return render_template("rede.html", app_name=APP_NAME, out=out)

@app.route("/admin")
def admin():
    return render_template("admin.html", stats=stats(), app_name=APP_NAME)

# =====================================================
# INIT
# =====================================================
if __name__ == "__main__":
    init_db()
    if stats()["chunks"] == 0:
        index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
    app.run(debug=True, port=5000)
