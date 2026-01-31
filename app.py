import os
import re
import sqlite3
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash
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

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)

# =====================================================
# RESPOSTAS PRONTAS (CURADORIA CLÍNICA EXPANDIDA)
# Observação importante:
# - NÃO removi nenhuma das que você já tinha
# - Mantive as originais
# - Acrescentei novas
# - E garanti 100 botões com respostas (as que não tiverem resposta específica
#   recebem uma resposta segura e orientativa, sem expor casos)
# =====================================================
RESPOSTAS_PRONTAS = {
    # =================================================
    # --- RELAÇÕES E VÍNCULOS (SUAS ORIGINAIS) ---
    # =================================================
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
        <h3>Zona de Cuidado: Evite relações duplas.</h3>
        <p>Se for um evento grande (show, palestra), tudo bem. Se for íntimo (aniversário, jantar na casa de amigos em comum), sua presença pode inibir o paciente ou configurar uma relação pessoal que interfere na profissional.</p>
        <p><strong>Dica:</strong> Se o encontro for inevitável, mantenha postura discreta e profissional. Não aja como "amiga" íntima.</p>
    </div>
    """,

    "Devo cumprimentar meu paciente na rua?": """
    <div class="resposta-humanizada">
        <h3>Regra de ouro: espere o paciente reagir.</h3>
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
        <h3>Cuidado com a auto-revelação.</h3>
        <p>A terapia é sobre o paciente, não sobre você. Falar da sua vida só é válido se tiver um <strong>objetivo terapêutico claro</strong> para ajudar aquele paciente naquele momento.</p>
        <p>Se for para desabafar ou "ficar amigo", é erro técnico e ético.</p>
    </div>
    """,

    # =================================================
    # --- PRONTUÁRIOS E DOCUMENTOS (SUAS ORIGINAIS) ---
    # =================================================
    "Eu sou obrigada fazer anotações?": """
    <div class="resposta-humanizada">
        <h3>Sim, é obrigatório.</h3>
        <p>Manter prontuário não é opcional. É dever do psicólogo (Resolução CFP 01/2009) para garantir a continuidade do serviço e a defesa técnica em caso de processos.</p>
        <p><strong>O que anotar?</strong> Evolução, datas, procedimentos e encaminhamentos. Não precisa ser a transcrição da fala, mas a síntese técnica.</p>
    </div>
    """,

    "O que é obrigatório eu anotar no prontuário?": """
    <div class="resposta-humanizada">
        <h3>Itens obrigatórios (Resolução CFP 01/2009):</h3>
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
            <li><strong>Confidencialidade:</strong> Senha forte e proteção adequada.</li>
            <li><strong>Autenticidade:</strong> Idealmente com assinatura digital quando aplicável.</li>
            <li><strong>Permanência:</strong> Backup seguro por tempo adequado.</li>
        </ul>
        <div class="alert-box warning">Nota simples no celular ou arquivo sem proteção não é prontuário seguro.</div>
    </div>
    """,

    "Como devo guardar prontuários antigos?": """
    <div class="resposta-humanizada">
        <h3>Prazo mínimo: 5 anos.</h3>
        <p>Você deve guardar os documentos por no mínimo 5 anos, mantendo o sigilo absoluto (arquivo trancado ou digital protegido).</p>
    </div>
    """,

    "O que fazer se o juiz pedir o prontuário?": """
    <div class="resposta-humanizada">
        <h3>Não entregue tudo automaticamente.</h3>
        <p>O sigilo protege o paciente. Se intimada:</p>
        <ol>
            <li>Tente responder via <strong>relatório</strong> respondendo apenas aos quesitos do juiz.</li>
            <li>Se houver exigência de prontuário, solicite medidas de proteção (ex.: segredo de justiça) e entregue o <strong>mínimo necessário</strong>.</li>
        </ol>
        <p><em>Dica: consulte a COF do seu CRP com o ofício em mãos.</em></p>
    </div>
    """,

    # =================================================
    # --- SIGILO E FAMÍLIA (SUAS ORIGINAIS) ---
    # =================================================
    "Ao dar devolutiva para os pais apos atendimento devo contar tudo que a criança disse?": """
    <div class="resposta-humanizada">
        <h3>Não. A criança também tem direito ao sigilo.</h3>
        <p>O Art. 13 do Código de Ética é claro: aos responsáveis, comunica-se apenas o <strong>estritamente essencial</strong> para promover medidas em benefício da criança.</p>
        <p><strong>O que falar?</strong> Riscos, orientações de manejo, dinâmicas gerais. Evite expor confidências íntimas que não envolvam risco ou necessidade de proteção.</p>
    </div>
    """,

    "O que posso compartilhar em uma supervisão?": """
    <div class="resposta-humanizada">
        <h3>Apenas o caso clínico, nunca a identidade.</h3>
        <p>Você pode discutir manejo e hipóteses, mas deve <strong>anonimizar</strong> o paciente. Evite detalhes que permitam identificação social.</p>
    </div>
    """,

    "Preciso ter um contato emergencial para todo paciente?": """
    <div class="resposta-humanizada">
        <h3>É uma medida de segurança recomendada.</h3>
        <p>Especialmente em casos com risco ou vulnerabilidade. Combine com o paciente quando esse contato pode ser acionado (situações excepcionais e justificadas).</p>
    </div>
    """,

    # =================================================
    # --- QUESTÕES ÉTICAS E SOCIAIS (SUAS ORIGINAIS) ---
    # =================================================
    "Posso atender de graça?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas cuide do enquadre.</h3>
        <p>Atendimento pro bono é permitido. O cuidado ético é não usar preço como propaganda para captação desleal e manter contrato claro.</p>
    </div>
    """,

    "Posso influenciar na orientação sexual do meu paciente?": """
    <div class="resposta-humanizada">
        <h3>Não. Isso é infração ética grave.</h3>
        <p><strong>Art. 2º do Código de Ética:</strong> é vedado induzir a convicções de orientação sexual.</p>
        <p>O papel do psicólogo é acolher, reduzir sofrimento e fortalecer autonomia e dignidade, não impor direção moral.</p>
    </div>
    """,

    "Existe psicologia evangélica?": """
    <div class="resposta-humanizada">
        <h3>Como ciência e profissão, a Psicologia é laica.</h3>
        <p>Você pode ter fé, mas sua prática técnica não pode ser religiosa. Respeite a fé do paciente sem impor crenças.</p>
    </div>
    """,

    "É proíbido falar sobre religião nas sessões?": """
    <div class="resposta-humanizada">
        <h3>Não. Falar SOBRE religião pode ser necessário.</h3>
        <p>Se a fé é importante para o paciente, ela faz parte da história dele. O que é vedado é impor crenças ou transformar a sessão em prática religiosa.</p>
    </div>
    """,

    "Posso divulgar o valor da sessão no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Pode informar, mas evite tom promocional.</h3>
        <p>Informar valores pode ser transparência. O cuidado ético é não usar "promoções", "descontos chamativos" ou promessas de resultado.</p>
    </div>
    """,

    "Preciso de contrato para terapia online?": """
    <div class="resposta-humanizada">
        <h3>Sim, é fortemente recomendado.</h3>
        <p>Combine por escrito: sigilo, plataforma, política de faltas, o que fazer se cair a internet, formas de contato e plano para emergências quando aplicável.</p>
    </div>
    """,

    # =================================================
    # --- ALIASES (para NÃO QUEBRAR botões do app) ---
    # =================================================
    "Ao dar devolutiva para os pais devo contar tudo?": """
    <div class="resposta-humanizada">
        <h3>Não. Conte apenas o estritamente essencial.</h3>
        <p>Aos responsáveis comunica-se o <strong>estritamente necessário</strong> para medidas em benefício do paciente. Evite expor confidências sem necessidade de proteção.</p>
    </div>
    """,

    "Posso influenciar na orientação sexual?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>É vedado ao psicólogo induzir ou pressionar a pessoa atendida quanto à orientação sexual. O cuidado é ético, acolhedor e baseado em autonomia.</p>
    </div>
    """,

    "Posso aceitar presentes?": """
    <div class="resposta-humanizada">
        <h3>Depende do valor e do significado.</h3>
        <p>Pequenos presentes simbólicos podem ocorrer. Presentes caros ou com cobrança implícita devem ser recusados com explicação ética.</p>
    </div>
    """,

    # =================================================
    # --- NOVAS RESPOSTAS DIRETAS (algumas já estavam) ---
    # =================================================
    "Existe cura gay?": """
    <div class="resposta-humanizada">
        <h3>Não existe “cura gay”.</h3>
        <p>Orientação sexual <strong>não é doença</strong> e não é algo a ser “curado”. O psicólogo atua para acolher, reduzir sofrimento e fortalecer autonomia.</p>
    </div>
    """,

    "O que responder quando pedem terapia de reversão?": """
    <div class="resposta-humanizada">
        <h3>Responda com firmeza e ética.</h3>
        <p>Explique que orientação sexual não é patologia e que o serviço psicológico não tem como finalidade "mudar" orientação. Você pode oferecer cuidado para sofrimento, culpa, ansiedade, conflitos familiares e discriminação.</p>
        <div class="alert-box tip">
            💡 <strong>Frase útil:</strong> “Posso te ajudar com o sofrimento que você está vivendo, mas não com a ideia de ‘mudar’ sua orientação sexual.”
        </div>
    </div>
    """,

    "Até onde vai o sigilo?": """
    <div class="resposta-humanizada">
        <h3>O sigilo é regra. Exceções são raras.</h3>
        <p>O sigilo protege a intimidade e o vínculo terapêutico. Em situações excepcionais, avalia-se o <strong>mínimo necessário</strong> e registra-se a decisão técnica.</p>
    </div>
    """,

    "Posso falar do caso com meu cônjuge ou amigo?": """
    <div class="resposta-humanizada">
        <h3>Não. Isso viola sigilo.</h3>
        <p>Discussão de caso deve ocorrer em contexto profissional (supervisão/equipe autorizada) e com anonimização.</p>
    </div>
    """,

    "Posso confirmar para alguém que a pessoa é minha paciente?": """
    <div class="resposta-humanizada">
        <h3>Evite confirmar.</h3>
        <p>Confirmar que alguém é seu paciente já é informação sigilosa. A forma segura é dizer que não pode confirmar nem negar por sigilo profissional.</p>
    </div>
    """,

    "Posso seguir paciente no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Em geral, não é recomendado.</h3>
        <p>Seguir/ser seguida pode criar relação dual e interferir no enquadre. Se houver necessidade excepcional, combine limites claros e registre o motivo.</p>
    </div>
    """,

    "Posso responder mensagens do paciente fora do horário?": """
    <div class="resposta-humanizada">
        <h3>Defina regras claras.</h3>
        <p>Combine horário, canal e finalidade (ex.: remarcação). Atendimento não deve virar plantão informal permanente.</p>
    </div>
    """,

    "Posso usar WhatsApp pessoal com pacientes?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas exige enquadre.</h3>
        <p>Use preferencialmente para logística. Oriente privacidade do aparelho e deixe claro que não é canal de urgência.</p>
    </div>
    """,

    "Posso atender amigos?": """
    <div class="resposta-humanizada">
        <h3>Evite. Se atender, é zona de risco ético.</h3>
        <p>Relação dual aumenta conflito de interesse e compromete neutralidade e sigilo. O mais seguro é encaminhar.</p>
    </div>
    """,

    "Posso atender familiares?": """
    <div class="resposta-humanizada">
        <h3>Em geral, não é recomendado.</h3>
        <p>Atender familiares próximos costuma gerar conflitos de interesse e ameaça ao sigilo. Prefira encaminhar.</p>
    </div>
    """,

    "Posso cobrar multa por falta?": """
    <div class="resposta-humanizada">
        <h3>Pode, se estiver acordado previamente.</h3>
        <p>Política de faltas deve ser transparente, por escrito, e manejada com respeito. Explique possibilidades de remarcação quando fizer sentido clínico.</p>
    </div>
    """,

    "Como lidar com inadimplência?": """
    <div class="resposta-humanizada">
        <h3>Contrato, conversa e dignidade.</h3>
        <p>Relembre o acordo, proponha renegociação/encaminhamento e registre. Em cobranças, preserve sigilo (não exponha que é paciente).</p>
    </div>
    """,

    "Posso emitir declaração de comparecimento?": """
    <div class="resposta-humanizada">
        <h3>Sim.</h3>
        <p>Declaração é documento simples: data/horário do atendimento e identificação do profissional. Evite conteúdo clínico desnecessário.</p>
    </div>
    """,

    "Posso gravar a sessão?": """
    <div class="resposta-humanizada">
        <h3>Só com consentimento claro.</h3>
        <p>Combine finalidade, armazenamento seguro, tempo de guarda e quem terá acesso. Evite se não houver real necessidade.</p>
    </div>
    """,

    "Posso usar IA para escrever prontuário?": """
    <div class="resposta-humanizada">
        <h3>Somente com extremo cuidado e sem expor dados.</h3>
        <p>Evite inserir dados identificáveis em ferramentas externas. Se usar, mantenha texto genérico, revise tudo e preserve sigilo. A responsabilidade é do psicólogo.</p>
    </div>
    """,

    "Posso atender em local público (cafeteria)?": """
    <div class="resposta-humanizada">
        <h3>Não é recomendado.</h3>
        <p>Há risco de quebra de sigilo, interrupções e falta de privacidade. Psicoterapia exige ambiente protegido.</p>
    </div>
    """,
}

# =====================================================
# 100 DÚVIDAS ÉTICAS (BOTÕES)
# - Não removi as suas
# - Acrescentei até fechar 100
# - Todas terão resposta: específica (quando existir) ou orientativa (fallback)
# =====================================================
QUICK_QUESTIONS = [
    # Suas que já existiam
    "O que fazer se o juiz pedir o prontuário?",
    "Sou obrigada a fazer anotações?",
    "Paciente pediu para não registrar no prontuário",
    "Devo cumprimentar meu paciente na rua?",
    "Posso aceitar presentes?",
    "Posso atender amigos?",
    "Posso atender familiares de ex-pacientes?",
    "Como lidar com inadimplência?",
    "Posso cobrar multa por falta?",
    "Existe cura gay?",
    "Posso influenciar na orientação sexual?",
    "Existe psicologia evangélica?",
    "É proíbido falar sobre religião nas sessões?",
    "Posso seguir paciente no Instagram?",
    "Posso divulgar o valor da sessão no Instagram?",
    "Preciso de contrato para terapia online?",

    # Mais (total 100)
    "Posso confirmar para alguém que a pessoa é minha paciente?",
    "Posso falar do caso com meu cônjuge ou amigo?",
    "Até onde vai o sigilo?",
    "Quando posso quebrar o sigilo?",
    "Como agir se o paciente pede segredo absoluto?",
    "Como agir se um familiar pede informações do paciente?",
    "Posso responder e-mail de familiar sobre o paciente?",
    "Posso usar WhatsApp pessoal com pacientes?",
    "Posso responder mensagens fora do horário?",
    "Posso ligar para o paciente fora do combinado?",
    "Posso atender em local público (cafeteria)?",
    "Posso gravar a sessão?",
    "Posso autorizar o paciente a gravar a sessão?",
    "Posso usar IA para escrever prontuário?",
    "Posso usar IA para sugerir conduta clínica?",
    "Posso usar prontuários de forma digital?",
    "Como devo guardar prontuários antigos?",
    "O que é obrigatório eu anotar no prontuário?",
    "Paciente pediu cópia do prontuário: o que fazer?",
    "Posso negar um relatório solicitado?",
    "Posso emitir declaração de comparecimento?",
    "Posso emitir laudo psicológico para processo?",
    "Posso emitir relatório para escola?",
    "Posso emitir relatório para empresa do paciente?",
    "Posso colocar CID em relatório?",
    "Posso assinar documento sem avaliação suficiente?",
    "Posso orientar medicação ao paciente?",
    "Posso indicar psiquiatra específico?",
    "Posso receber comissão por encaminhamento?",
    "Posso fazer parceria com médico por indicação?",
    "Posso divulgar antes e depois da terapia?",
    "Posso postar depoimento de paciente?",
    "Posso prometer resultado na terapia?",
    "Posso divulgar prints de conversa (mesmo sem nome)?",
    "Posso divulgar fotos do consultório com agenda visível?",
    "Posso usar imagem de paciente em divulgação?",
    "Posso divulgar preço promocional?",
    "Posso fazer sorteio de sessões?",
    "Posso atender de graça?",
    "Posso oferecer primeira sessão gratuita como marketing?",
    "Posso atender amigos próximos?",
    "Posso atender familiares?",
    "Posso atender dois membros da mesma família individualmente?",
    "Posso atender casal e um dos parceiros individualmente?",
    "Posso atender ex-parceiro do paciente?",
    "Posso atender paciente que trabalha comigo?",
    "Posso atender paciente que é meu professor?",
    "Posso atender paciente que é meu chefe?",
    "Posso manter amizade com paciente durante o tratamento?",
    "Posso sair com paciente após encerramento?",
    "Quanto tempo esperar para relação social após alta?",
    "Posso aceitar convite para evento íntimo do paciente?",
    "Posso ir a eventos sociais em que meu paciente esta?",
    "Posso seguir paciente no Instagram com perfil profissional?",
    "Posso curtir posts do paciente?",
    "Posso ver stories do paciente?",
    "Posso bloquear paciente nas redes?",
    "Posso pesquisar o paciente no Google?",
    "Posso pesquisar o paciente nas redes por curiosidade?",
    "O que fazer se eu vir o paciente em app de namoro?",
    "Posso atender adolescente sem os pais saberem?",
    "O que falar para os pais sobre a terapia do filho?",
    "Ao dar devolutiva para os pais devo contar tudo?",
    "Ao dar devolutiva para os pais apos atendimento devo contar tudo que a criança disse?",
    "Posso atender criança sem presença do responsável na primeira sessão?",
    "Posso atender criança se os pais são divorciados e discordam?",
    "Preciso de consentimento dos dois responsáveis?",
    "Posso atender online com paciente em outro estado?",
    "Como garantir sigilo no atendimento online?",
    "Posso atender paciente dirigindo (no carro)?",
    "Posso atender paciente no trabalho dele?",
    "Posso atender por áudio no WhatsApp?",
    "Posso atender por mensagem (chat)?",
    "Preciso de contrato para terapia online?",
    "Posso cobrar sessão cancelada por internet ruim?",
    "O que fazer quando a internet cai na sessão?",
    "Posso remarcar sessão sem custo por motivo do paciente?",
    "Posso cobrar PIX adiantado?",
    "Posso cobrar pacote de sessões?",
    "Posso emitir recibo sem CPF do paciente?",
    "Posso emitir recibo em nome de terceiro?",
    "Posso recusar atendimento por conflito de valores?",
    "Posso recusar atendimento por falta de vaga?",
    "Como encerrar terapia de forma ética?",
    "Quando devo encaminhar um paciente?",
    "Posso encaminhar sem explicar motivo?",
    "O que fazer se eu errar com o paciente?",
    "Posso confrontar o paciente?",
    "Posso dar conselhos diretos ao paciente?",
    "Posso orar com o paciente na sessão?",
    "Existe cura gay?",
    "O que responder quando pedem terapia de reversão?",
    "Posso influenciar na orientação sexual do meu paciente?",
]

# =====================================================
# RESPOSTA PADRÃO (para perguntas novas sem resposta específica)
# =====================================================
def resposta_orientativa(pergunta: str) -> str:
    return f"""
    <div class="resposta-humanizada">
        <h3>Orientação ética para esta dúvida</h3>
        <p><strong>Pergunta:</strong> {pergunta}</p>
        <p>Esta é uma dúvida frequente e, em geral, a resposta ética passa por 4 critérios:</p>
        <ol>
            <li><strong>Sigilo e privacidade:</strong> reduzir exposição ao mínimo necessário.</li>
            <li><strong>Relações duais e conflito de interesse:</strong> evitar situações que confundam papéis.</li>
            <li><strong>Finalidade e necessidade:</strong> fazer apenas o que for tecnicamente justificável.</li>
            <li><strong>Registro e transparência:</strong> combinar limites e registrar decisões relevantes.</li>
        </ol>
        <div class="alert-box tip">
            💡 Se houver dúvida prática ou risco, procure orientação técnica no seu CRP (COF) e mantenha o foco no mínimo necessário.
        </div>
        <p class="muted">Dica: use os botões relacionados (sigilo, prontuário, redes sociais, documentos, relações duais) para comparar condutas.</p>
    </div>
    """

def garantir_100_respostas():
    # Garante que todas as perguntas dos botões tenham resposta exata
    for q in QUICK_QUESTIONS:
        if q not in RESPOSTAS_PRONTAS:
            RESPOSTAS_PRONTAS[q] = resposta_orientativa(q)

garantir_100_respostas()

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
    terms = query.lower().split()
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
# ROTAS
# =====================================================
@app.route("/", methods=["GET", "POST"])
def home():
    answer = None

    if request.method == "POST":
        # 1) Resetar Base
        if "load_bases" in request.form:
            clear_documents()
            index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
            flash("Cérebro ético atualizado com sucesso!", "success")
            return redirect(url_for("home"))

        # 2) Processar escolha (agora vem dos botões)
        q = request.form.get("q", "").strip()

        if q:
            # A) Match Exato (Prioridade Máxima)
            if q in RESPOSTAS_PRONTAS:
                answer = RESPOSTAS_PRONTAS[q]

            # B) Match Parcial (mantido como segurança, caso alguém poste manualmente)
            else:
                found_partial = False
                q_words = set(q.lower().replace("?", "").split())

                for key, val in RESPOSTAS_PRONTAS.items():
                    key_words = set(key.lower().replace("?", "").split())
                    if not key_words:
                        continue
                    if len(key_words.intersection(q_words)) >= max(1, int(len(key_words) * 0.7)):
                        answer = val
                        found_partial = True
                        break

                # C) Busca Genérica no Texto
                if not found_partial:
                    hits = simple_search(q)
                    if hits:
                        html_hits = "".join([
                            f"<div class='ref-card source-cfp'><div class='ref-body'>...{h}...</div></div>"
                            for h in hits
                        ])
                        answer = f"""
                        <div class="resposta-humanizada">
                            <h3>Resultados da Busca</h3>
                            <p>Não encontrei uma resposta exata para sua dúvida, mas veja trechos relacionados:</p>
                            {html_hits}
                            <div class="alert-box tip">💡 Use os botões para refinar a dúvida.</div>
                        </div>
                        """
                    else:
                        answer = """
                        <div class="resposta-humanizada">
                            <h3>Dúvida complexa</h3>
                            <div class="alert-box warning">
                                Não encontrei uma resposta específica no meu banco de dados atual.
                            </div>
                            <p>Use os botões por tema e procure termos como: <strong>sigilo</strong>, <strong>prontuário</strong>, <strong>documentos</strong>, <strong>família</strong>, <strong>redes sociais</strong>.</p>
                        </div>
                        """

            save_history(q, answer)

    return render_template(
        "home.html",
        app_name=APP_NAME,
        stats=stats(),
        history=get_history(50),
        answer=answer,
        quick_questions=QUICK_QUESTIONS
    )

@app.route("/admin")
def admin():
    return render_template("admin.html", stats=stats(), app_name=APP_NAME)

if __name__ == "__main__":
    init_db()
    if stats()["chunks"] == 0:
        index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
    app.run(debug=True, port=5000)
