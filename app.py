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

# =====================================================
# LINKS OFICIAIS
# (mantive as chaves antigas para não quebrar templates)
# =====================================================
LINKS_OFICIAIS = {
    "codigo_etica_pdf_2025": "https://site.cfp.org.br/wp-content/uploads/2012/07/codigo-de-etica-psicologia.pdf",
    "codigo_etica_pdf": "https://site.cfp.org.br/wp-content/uploads/2012/07/codigo-de-etica-psicologia.pdf",
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
# 100 DÚVIDAS ÉTICAS (BOTÕES)
# (mantive sua lista integral)
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
# HELPERS DE RESPOSTA (HTML)
# =====================================================
def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _make_answer(title: str, bullets: list[str], delicate: bool = True) -> str:
    warn = ""
    if delicate:
        warn = """
        <div class="alert-box warning">
          <strong>Questão delicada:</strong> se houver dúvida prática, consulte a COF do seu CRP e leve para supervisão.
        </div>
        """
    lis = "".join([f"<li>{_html_escape(b)}</li>" for b in bullets if b.strip()])
    return f"""
    <div class="resposta-humanizada">
      <h3>{_html_escape(title)}</h3>
      {warn}
      <ul>{lis}</ul>
    </div>
    """

# =====================================================
# RESPOSTAS ESPECÍFICAS (OVERRIDES IMPORTANTES)
# (aqui entram as "fechadas" que você pediu explicitamente)
# =====================================================
OVERRIDES = {
    "Posso falar do caso com meu cônjuge ou amigo?": _make_answer(
        "Não. Isso viola o sigilo profissional.",
        [
            "Não é permitido compartilhar informações clínicas com cônjuge/amigos, mesmo sem citar nome, se houver risco de identificação ou exposição.",
            "Se isso te afetar emocionalmente, leve o tema para supervisão (e não para conversas pessoais).",
            "Foque em discutir o manejo clínico em espaço profissional e com anonimização.",
        ],
        delicate=True
    ),

    "Até onde vai o sigilo?": _make_answer(
        "O sigilo é a regra e protege a intimidade do paciente.",
        [
            "Você não deve revelar que alguém é seu paciente nem conteúdo de sessões.",
            "Exceções são raras: risco grave e atual, dever legal ou ordem judicial — sempre pelo mínimo necessário.",
            "Em situações de violência/violação de direitos (especialmente envolvendo crianças/adolescentes), o encaminhamento à rede de proteção pode ser necessário; registre a justificativa e compartilhe somente o essencial.",
            "Sempre que possível, combine limites de sigilo no início e retome quando a situação exigir.",
        ],
        delicate=True
    ),

    "Quando posso quebrar o sigilo?": _make_answer(
        "A quebra de sigilo é excepcional e deve ser mínima.",
        [
            "Considere apenas em risco grave e atual, dever legal, ou ordem judicial.",
            "Compartilhe somente o mínimo necessário e registre a decisão técnica.",
            "Quando possível, informe o paciente sobre limites e sobre o que será comunicado.",
        ],
        delicate=True
    ),

    "Existe cura gay?": _make_answer(
        "Não. Orientação sexual não é doença.",
        [
            "O psicólogo não deve prometer, oferecer ou conduzir intervenção para “mudar” orientação sexual.",
            "Atuação ética: acolher sofrimento, fortalecer autonomia, lidar com discriminação e conflitos.",
        ],
        delicate=True
    ),

    "Posso influenciar na orientação sexual do meu paciente?": _make_answer(
        "Não. É vedado induzir convicções e preconceitos.",
        [
            "O psicólogo não deve direcionar o paciente a mudar orientação sexual.",
            "Atuação ética: acolher, reduzir sofrimento e fortalecer autonomia.",
        ],
        delicate=True
    ),
}

# =====================================================
# GERAÇÃO DE RESPOSTAS PARA TODAS AS QUESTÕES
# - todas as perguntas terão resposta específica
# - sempre com nota "Questão delicada..." quando apropriado
# =====================================================
def generate_answer_for_question(q: str) -> str:
    if q in OVERRIDES:
        return OVERRIDES[q]

    ql = (q or "").lower()

    # SIGILO / TERCEIROS
    if "sigilo" in ql or "confirmar" in ql or "crime" in ql or "familiar" in ql or "terceiro" in ql:
        if "confirmar" in ql:
            return _make_answer(
                "Evite confirmar. O vínculo terapêutico é sigiloso.",
                [
                    "A conduta mais segura é não confirmar nem negar: “Por sigilo profissional, não posso confirmar nem negar.”",
                    "Evite conversas informais sobre pacientes com terceiros.",
                ],
                delicate=True
            )
        if "grupo" in ql or "whatsapp" in ql:
            return _make_answer(
                "Não é adequado discutir caso em grupo aberto.",
                [
                    "Mesmo em grupo “profissional”, há risco de quebra de sigilo e exposição.",
                    "Discussão de caso deve ser em supervisão/equipe autorizada e com anonimização rigorosa.",
                ],
                delicate=True
            )
        if "e-mail" in ql or "email" in ql:
            return _make_answer(
                "Cuidado: não compartilhe informações do paciente com familiares por e-mail.",
                [
                    "Só compartilhe o mínimo necessário, com autorização e finalidade clara.",
                    "Evite detalhes clínicos por canais inseguros; registre o motivo e o conteúdo essencial comunicado.",
                ],
                delicate=True
            )
        if "quebrar" in ql:
            return _make_answer(
                "Quebra de sigilo é exceção e deve ser mínima.",
                [
                    "Considere apenas em risco grave e atual, dever legal ou ordem judicial.",
                    "Compartilhe somente o essencial e registre a decisão técnica.",
                ],
                delicate=True
            )
        return _make_answer(
            "Sigilo é regra. Exceções são raras e justificadas.",
            [
                "Use o princípio do mínimo necessário.",
                "Registre sua decisão técnica quando houver exceção.",
                "Em dúvida, consulte o CRP (COF) e supervisão.",
            ],
            delicate=True
        )

    # PRONTUÁRIO / REGISTRO / GUARDA
    if "prontu" in ql or "anot" in ql or "guardar" in ql or "digital" in ql or "ia" in ql:
        if "ia" in ql:
            return _make_answer(
                "Use com extrema cautela. Priorize sigilo.",
                [
                    "Evite inserir dados identificáveis em ferramentas externas.",
                    "Se usar, mantenha texto genérico e revise tudo; a responsabilidade é do psicólogo.",
                    "Considere alternativas: modelos locais/offline e registro sintético.",
                ],
                delicate=True
            )
        if "digital" in ql:
            return _make_answer(
                "Pode ser digital, desde que preserve sigilo e segurança.",
                [
                    "Acesso restrito, senha forte e backups.",
                    "Evite compartilhamento automático e dispositivos desprotegidos.",
                ],
                delicate=True
            )
        if "obrigatório" in ql or "obrigatoria" in ql:
            return _make_answer(
                "Registre o essencial técnico.",
                [
                    "Identificação mínima necessária, objetivos, evolução, condutas e encaminhamentos.",
                    "Evite detalhes íntimos desnecessários.",
                ],
                delicate=True
            )
        if "cópia" in ql or "copia" in ql:
            return _make_answer(
                "Em geral, o paciente pode solicitar acesso, com cuidado na forma.",
                [
                    "Avalie a forma mais adequada: relatório/síntese, preservando terceiros e evitando dano.",
                    "Registre a decisão e o que foi entregue.",
                ],
                delicate=True
            )
        if "guardar" in ql or "quanto tempo" in ql:
            return _make_answer(
                "Guarde registros com sigilo e acesso restrito.",
                [
                    "Arquivo físico: local trancado.",
                    "Arquivo digital: proteção por senha, backup e controle de acesso.",
                    "Registre sua política de guarda e descarte seguro.",
                ],
                delicate=True
            )
        return _make_answer(
            "Prontuário é dever profissional e deve ser protegido.",
            [
                "Registre o essencial técnico, preserve sigilo e mantenha segurança.",
                "Em dúvida, consulte CRP e supervisão.",
            ],
            delicate=True
        )

    # DOCUMENTOS / RELATÓRIO / LAUDO / DECLARAÇÃO
    if "relatório" in ql or "relatorio" in ql or "laudo" in ql or "declara" in ql or "cid" in ql:
        if "declara" in ql:
            return _make_answer(
                "Declaração de comparecimento é possível e deve ser simples.",
                [
                    "Inclua data/horário e identificação do profissional.",
                    "Evite conteúdo clínico desnecessário.",
                ],
                delicate=False
            )
        if "cid" in ql:
            return _make_answer(
                "CID em documento exige cautela e finalidade clara.",
                [
                    "Evite expor diagnóstico sem necessidade e sem consentimento.",
                    "Use o mínimo necessário e registre a justificativa.",
                ],
                delicate=True
            )
        if "escola" in ql or "empresa" in ql or "inss" in ql:
            return _make_answer(
                "Documento para terceiros deve ser mínimo e com finalidade clara.",
                [
                    "Solicite autorização e delimite o que será informado.",
                    "Evite detalhamento íntimo; foque em informações essenciais e medidas de apoio.",
                    "Registre a solicitação, a autorização e o conteúdo entregue.",
                ],
                delicate=True
            )
        if "juiz" in ql:
            return _make_answer(
                "Não entregue tudo automaticamente.",
                [
                    "Prefira relatório respondendo ao que foi solicitado, com mínimo necessário.",
                    "Se houver exigência, peça proteção (segredo de justiça) e registre.",
                ],
                delicate=True
            )
        return _make_answer(
            "Documentos devem respeitar sigilo e finalidade.",
            [
                "Produza apenas o necessário e tecnicamente justificável.",
                "Evite expor paciente e terceiros.",
                "Registre o motivo e o conteúdo essencial emitido.",
            ],
            delicate=True
        )

    # REDES SOCIAIS / CONTATO
    if "instagram" in ql or "stories" in ql or "curtir" in ql or "google" in ql or "bloquear" in ql:
        if "seguir" in ql:
            return _make_answer(
                "Em geral, evite seguir paciente.",
                [
                    "Redes sociais aumentam risco de relação dual e exposição.",
                    "Se necessário, alinhe limites explicitamente e registre a decisão.",
                ],
                delicate=True
            )
        if "curtir" in ql or "stories" in ql:
            return _make_answer(
                "Evite interações que confundam papéis.",
                [
                    "Curtidas e visualizações podem ser percebidas como proximidade pessoal e expor vínculo.",
                    "Se o tema aparecer, trabalhe em sessão.",
                ],
                delicate=True
            )
        if "google" in ql:
            return _make_answer(
                "Evite pesquisar paciente por curiosidade.",
                [
                    "Pode violar privacidade e distorcer o vínculo.",
                    "Só considere em situações excepcionais e justificáveis (segurança), preferindo transparência e supervisão.",
                ],
                delicate=True
            )
        if "bloquear" in ql:
            return _make_answer(
                "Pode bloquear se for necessário para proteger o enquadre.",
                [
                    "Você pode explicar como política profissional: não manter contato por redes.",
                    "Registre se houve impacto no processo.",
                ],
                delicate=True
            )
        return _make_answer(
            "Mantenha limites digitais claros.",
            [
                "Evite interações em redes sociais para proteger sigilo e enquadre.",
                "Se necessário, alinhe em sessão e registre.",
            ],
            delicate=True
        )

    # ONLINE / WHATSAPP / CHAT / ÁUDIO
    if "online" in ql or "internet" in ql or "whatsapp" in ql or "chat" in ql or "áudio" in ql or "audio" in ql:
        if "contrato" in ql:
            return _make_answer(
                "Sim, contrato é recomendado no online.",
                [
                    "Defina plataforma, sigilo, faltas, queda de internet e canal de contato.",
                ],
                delicate=False
            )
        if "cai" in ql or "internet" in ql:
            return _make_answer(
                "Tenha protocolo para queda de conexão.",
                [
                    "Aguardar alguns minutos, tentar reconectar e confirmar por mensagem.",
                    "Remarcar conforme política acordada.",
                ],
                delicate=False
            )
        if "áudio" in ql or "chat" in ql:
            return _make_answer(
                "Pode ser possível, mas aumenta riscos.",
                [
                    "Mensageria/áudio elevam risco de vazamento e confundem enquadre.",
                    "Se usar, estabeleça regras claras e registre.",
                ],
                delicate=True
            )
        if "dirigindo" in ql or "trabalho" in ql:
            return _make_answer(
                "Evite se não houver privacidade e segurança.",
                [
                    "Atendimento exige ambiente protegido.",
                    "Se o paciente estiver dirigindo ou em local público, oriente a parar ou remarcar.",
                ],
                delicate=True
            )
        if "gravar" in ql:
            return _make_answer(
                "Somente com consentimento explícito e necessidade.",
                [
                    "Defina finalidade, guarda e acesso.",
                    "Gravação aumenta risco de vazamento.",
                ],
                delicate=True
            )
        return _make_answer(
            "Atendimento online exige regras claras.",
            [
                "Ambiente privado e fone de ouvido.",
                "Plano para queda de internet.",
                "Limites de mensagens para logística.",
            ],
            delicate=True
        )

    # HONORÁRIOS / PAGAMENTO / PROMOÇÃO
    if "honor" in ql or "cobrar" in ql or "multa" in ql or "inadimpl" in ql or "pix" in ql or "pacote" in ql or "gratuita" in ql or "de graça" in ql:
        if "multa" in ql or "falta" in ql:
            return _make_answer(
                "Pode cobrar, se estiver combinado previamente.",
                [
                    "Política de faltas deve ser transparente e por escrito.",
                    "Mantenha manejo respeitoso e registre combinados.",
                ],
                delicate=True
            )
        if "inadimpl" in ql:
            return _make_answer(
                "Lide com dignidade e contrato claro.",
                [
                    "Relembre o combinado, proponha renegociação e registre.",
                    "Evite exposição do paciente em cobranças.",
                ],
                delicate=True
            )
        if "pix" in ql:
            return _make_answer(
                "Pode solicitar pagamento antecipado, se acordado.",
                [
                    "Defina cancelamentos, remarcação e reembolso.",
                ],
                delicate=False
            )
        if "pacote" in ql:
            return _make_answer(
                "Pode, com transparência e regras claras.",
                [
                    "Defina validade, cancelamento e o que ocorre em caso de alta/encerramento.",
                ],
                delicate=True
            )
        if "de graça" in ql or "gratuita" in ql:
            return _make_answer(
                "Pode atender gratuitamente, com enquadre claro.",
                [
                    "Defina regras, limites e duração do acordo.",
                    "Evite usar como captação promocional.",
                ],
                delicate=True
            )
        return _make_answer(
            "Honorários exigem transparência e enquadre.",
            [
                "Registre política de faltas e pagamentos.",
                "Evite promessas e captação desleal.",
            ],
            delicate=True
        )

    # RELAÇÕES DUAIS / FAMÍLIA / AMIGOS / CASAL
    if "amig" in ql or "famil" in ql or "casal" in ql or "professor" in ql or "chefe" in ql or "social" in ql:
        return _make_answer(
            "Em geral, evite relações duais.",
            [
                "Atender amigos/familiares/casal+individual com o mesmo profissional eleva risco de conflito de interesse e quebra de sigilo.",
                "Se inevitável, explicite limites, avalie riscos e registre; frequentemente o melhor é encaminhar.",
            ],
            delicate=True
        )

    # ENCERRAMENTO / ENCAMINHAMENTO / SUPERVISÃO
    if "encerrar" in ql or "encaminh" in ql or "supervis" in ql:
        return _make_answer(
            "Encerramento e encaminhamento devem ser cuidadosos e registrados.",
            [
                "Evite abandono: prepare, comunique e encaminhe quando necessário.",
                "Registre o encerramento e orientações essenciais.",
            ],
            delicate=True
        )

    # DEFAULT
    return _make_answer(
        "Orientação ética geral",
        [
            "Considere sigilo, limites, finalidade e mínimo necessário.",
            "Registre combinados importantes.",
            "Em dúvida, supervisão e CRP (COF).",
        ],
        delicate=True
    )

# =====================================================
# RESPOSTAS PARA TODAS AS QUESTÕES
# (agora sim: todas terão resposta específica)
# =====================================================
RESPOSTAS_GERADAS = {q: generate_answer_for_question(q) for q in QUICK_QUESTIONS}

# =====================================================
# AGRUPAMENTO: OBJETIVAS EM CIMA / ZONA EMBAIXO
# (objetiva = tem override ou resposta "fechada" no RESPOSTAS_PRONTAS)
# =====================================================
def build_quick_groups():
    direct = [{"text": q} for q in QUICK_QUESTIONS if q in RESPOSTAS_PRONTAS or q in OVERRIDES]
    care = [{"text": q} for q in QUICK_QUESTIONS if q not in RESPOSTAS_PRONTAS and q not in OVERRIDES]
    return direct, care

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
    terms = (query or "").lower().split()
    keywords = [t for t in terms if len(t) > 3]
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
# CONTRATO / HONORÁRIOS / POLÍTICAS / REDE
# (mantive suas funções exatamente como vinham)
# =====================================================
def gerar_contrato_texto(data: dict) -> str:
    modalidade = data.get("modalidade", "Online")
    plataforma = data.get("plataforma", "Google Meet")
    duracao = data.get("duracao", "50")
    frequencia = data.get("frequencia", "semanal")
    canal = data.get("canal", "WhatsApp")
    prazo_cancel = data.get("prazo_cancel", "24")
    falta_cobra = data.get("falta_cobra", "sim")
    atraso = data.get("atraso", "15")
    queda = data.get("queda", "10")
    pagamento = data.get("pagamento", "pix")
    recibo = data.get("recibo", "sim")
    reembolso = data.get("reembolso", "nao")
    emergencias = data.get("emergencias", "sim")
    sigilo = data.get("sigilo", "sim")
    grava = data.get("grava", "nao")

    detalhe_modalidade = (
        "Atendimento presencial em ambiente privativo, com início e término conforme horário agendado."
        if modalidade.lower() == "presencial"
        else f"Atendimento online por {plataforma}, com orientações de privacidade (local reservado e, se possível, uso de fone)."
    )
    falta_txt = "Sessões não desmarcadas dentro do prazo são cobradas." if falta_cobra == "sim" else "Sessões não desmarcadas dentro do prazo podem ser remanejadas conforme disponibilidade e critério."
    recibo_txt = "Recibo pode ser emitido mediante solicitação." if recibo == "sim" else "Recibo não é emitido."
    reembolso_txt = "Em caso de interrupção do serviço, valores antecipados podem ser ajustados conforme sessões realizadas." if reembolso == "sim" else "Não há reembolso automático para faltas ou cancelamentos fora do prazo."
    emerg_txt = "Este serviço não é plantão de urgência. Em risco imediato, recomenda-se acionar rede de apoio e serviços locais." if emergencias == "sim" else "Este serviço não realiza atendimentos de urgência."
    sig_txt = "O sigilo profissional é regra. Exceções são raras e seguem princípio do mínimo necessário." if sigilo == "sim" else "O sigilo profissional orienta a prática, com cuidado especial para privacidade."
    grava_txt = "Gravações não são permitidas sem consentimento explícito das partes e finalidade justificada." if grava == "nao" else "Gravações podem ocorrer apenas com consentimento explícito e acordo sobre guarda e acesso."

    return f"""CONTRATO TERAPÊUTICO (MODELO)

1) Modalidade e setting
- Modalidade: {modalidade}
- {detalhe_modalidade}

2) Duração e frequência
- Duração média da sessão: {duracao} minutos
- Frequência sugerida: {frequencia}

3) Comunicação fora da sessão
- Canal de contato: {canal}
- Finalidade: logística (remarcação, confirmação e avisos)
- Mensagens longas são preferencialmente tratadas em sessão.

4) Cancelamentos, faltas e atrasos
- Prazo para desmarcação: {prazo_cancel} horas
- Tolerância de atraso: {atraso} minutos (respeitando o horário final)
- Faltas: {falta_txt}

5) Atendimento online e queda de conexão (se aplicável)
- Em queda: aguardar {queda} minutos e tentar reconectar
- Se não retomar: registrar tentativa e remarcar conforme política.

6) Pagamento e recibos
- Forma de pagamento: {pagamento}
- {recibo_txt}
- {reembolso_txt}

7) Sigilo e privacidade
- {sig_txt}

8) Gravações
- {grava_txt}

9) Limites e emergências
- {emerg_txt}

10) Encerramento
- Encerramento por alta, acordo, limites de agenda ou indicação clínica.
- Quando possível, será trabalhado em sessão, com orientações e encaminhamentos.

Observação
Este documento é um modelo informacional e pode ser adaptado conforme contexto e critérios profissionais.
"""

def calc_honorarios(d: dict) -> dict:
    custos_fixos = float(d.get("custos_fixos", 0) or 0)
    custos_variaveis_mes = float(d.get("custos_variaveis_mes", 0) or 0)
    pro_labore = float(d.get("pro_labore", 0) or 0)
    impostos_perc = float(d.get("impostos_perc", 0) or 0) / 100.0
    semanas_mes = float(d.get("semanas_mes", 4.3) or 4.3)

    sessoes_semana = float(d.get("sessoes_semana", 0) or 0)
    duracao_min = float(d.get("duracao_min", 50) or 50)
    admin_min = float(d.get("admin_min", 10) or 10)
    faltas_perc = float(d.get("faltas_perc", 0) or 0) / 100.0

    custo_total_mes = custos_fixos + custos_variaveis_mes + pro_labore
    sessoes_mes_brutas = sessoes_semana * semanas_mes
    sessoes_mes_liquidas = max(0.0, sessoes_mes_brutas * (1.0 - faltas_perc))

    if sessoes_mes_liquidas <= 0:
        return {"ok": False, "erro": "Defina sessões por semana e faltas em um valor que gere ao menos 1 sessão/mês efetiva."}

    if impostos_perc >= 0.95:
        impostos_perc = 0.95

    receita_bruta_necessaria = custo_total_mes / max(0.01, (1.0 - impostos_perc))
    preco_min_sessao = receita_bruta_necessaria / sessoes_mes_liquidas

    tempo_por_sessao_min = duracao_min + admin_min
    horas_trabalho_mes = (tempo_por_sessao_min * sessoes_mes_brutas) / 60.0
    if horas_trabalho_mes <= 0:
        horas_trabalho_mes = 0.1

    receita_por_hora_bruta = (preco_min_sessao * sessoes_mes_liquidas) / horas_trabalho_mes

    return {
        "ok": True,
        "custo_total_mes": round(custo_total_mes, 2),
        "receita_bruta_necessaria": round(receita_bruta_necessaria, 2),
        "sessoes_mes_brutas": round(sessoes_mes_brutas, 1),
        "sessoes_mes_liquidas": round(sessoes_mes_liquidas, 1),
        "preco_min_sessao": round(preco_min_sessao, 2),
        "tempo_por_sessao_min": round(tempo_por_sessao_min, 0),
        "horas_trabalho_mes": round(horas_trabalho_mes, 1),
        "receita_por_hora_bruta": round(receita_por_hora_bruta, 2),
    }

def gerar_politica(data: dict) -> dict:
    tipo = data.get("tipo", "faltas")
    modalidade = data.get("modalidade", "Online")
    prazo = data.get("prazo", "24")
    atraso = data.get("atraso", "15")
    canal = data.get("canal", "WhatsApp")
    falta_cobra = data.get("falta_cobra", "sim")
    reembolso = data.get("reembolso", "nao")
    mensagens = data.get("mensagens", "logistica")
    queda = data.get("queda", "10")
    pagamento = data.get("pagamento", "pix")

    base_header = "POLÍTICA (TEXTO PRONTO PARA COPIAR)\n\n"

    if tipo == "faltas":
        texto = f"""{base_header}Política de cancelamento e faltas

- Prazo para desmarcação: {prazo} horas.
- Atrasos: tolerância de {atraso} minutos, respeitando o horário final.
- Falta sem aviso ou cancelamento fora do prazo: {"sessão é cobrada" if falta_cobra == "sim" else "pode ser remanejada conforme disponibilidade e critério"}.
- Canal para desmarcação: {canal}.
"""
        return {"titulo": "Faltas e cancelamentos", "texto": texto}

    if tipo == "mensagens":
        if mensagens == "logistica":
            regra = "Mensagens são destinadas apenas à logística (remarcação, confirmação e avisos)."
        elif mensagens == "curtas":
            regra = "Mensagens devem ser curtas e objetivas. Conteúdos terapêuticos serão priorizados em sessão."
        else:
            regra = "Mensagens não substituem a sessão. Em caso de necessidade importante, combinaremos o melhor encaminhamento."

        texto = f"""{base_header}Política de mensagens e contato fora da sessão

- Canal principal: {canal}.
- {regra}
- Este serviço não funciona como plantão de urgência.
"""
        return {"titulo": "Mensagens e contato", "texto": texto}

    if tipo == "reembolso":
        texto = f"""{base_header}Política de pagamentos e reembolso

- Forma de pagamento: {pagamento}.
- Reembolso: {"pode haver ajuste proporcional em caso de interrupção do serviço, conforme sessões realizadas" if reembolso == "sim" else "não há reembolso automático para faltas ou cancelamentos fora do prazo"}.
"""
        return {"titulo": "Pagamentos e reembolso", "texto": texto}

    if tipo == "online":
        texto = f"""{base_header}Protocolo de atendimento online

- Modalidade: {modalidade}.
- Recomenda-se ambiente privado e uso de fone.
- Em queda de conexão: aguardar {queda} minutos e tentar reconectar.
- Se não retomar: confirmar por {canal} e remarcar conforme disponibilidade.
"""
        return {"titulo": "Atendimento online", "texto": texto}

    if tipo == "sigilo":
        texto = f"""{base_header}Política de sigilo e privacidade

- O sigilo profissional é regra e protege a intimidade e o vínculo terapêutico.
- Informações só são compartilhadas em situações excepcionais, seguindo o princípio do mínimo necessário.
"""
        return {"titulo": "Sigilo e privacidade", "texto": texto}

    return {"titulo": "Política", "texto": f"{base_header}Escolha uma política para gerar um texto pronto."}

def gerar_rede(data: dict) -> dict:
    destino = data.get("destino", "psiquiatria")
    canal = data.get("canal", "WhatsApp")
    inclui_autorizacao = data.get("autorizacao", "sim")

    autorizacao_txt = (
        "Antes de qualquer contato com terceiros, solicite autorização por escrito do paciente (ou responsável legal), delimitando o que pode ser compartilhado e com qual finalidade.\n\n"
        if inclui_autorizacao == "sim" else ""
    )

    if destino == "psiquiatria":
        texto = f"""ROTEIRO DE REDE: Psiquiatria

{autorizacao_txt}Mensagem para encaminhamento
Canal sugerido: {canal}

Olá, tudo bem?
Sou psicóloga e estou acompanhando a pessoa em psicoterapia. Com autorização expressa, gostaria de encaminhar para avaliação psiquiátrica.
"""
        return {"titulo": "Encaminhamento para Psiquiatria", "texto": texto}

    if destino == "autorizacao":
        texto = """MODELO: Autorização para contato com terceiros

Eu, ______________________________, autorizo a psicóloga ______________________________ (CRP ________) a realizar contato profissional com ______________________________, com a finalidade de ______________________________.
"""
        return {"titulo": "Autorização por escrito", "texto": texto}

    return {"titulo": "Rede", "texto": "Escolha um destino para gerar um roteiro."}

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
            # agora TODAS as perguntas têm resposta específica (gerada)
            answer = RESPOSTAS_GERADAS.get(q) or resposta_orientativa(q)
            save_history(q, answer)

    direct_questions, care_questions = build_quick_groups()

    return render_template(
        "home.html",
        app_name=APP_NAME,
        stats=stats(),
        history=get_history(50),
        answer=answer,
        direct_questions=direct_questions,
        care_questions=care_questions
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
    # mantive o "cérebro" disponível
    if stats()["chunks"] == 0:
        index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
    app.run(debug=True, port=5000)
