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
# - Acrescentei várias novas + aliases para bater com os botões
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

    # =================================================
    # --- SIGILO E FAMÍLIA (SUAS ORIGINAIS) ---
    # =================================================
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
        <p>Especialmente em casos com risco de vida, surto ou vulnerabilidade. Tenha o contato anotado e combine com o paciente em que situações extremas aquele contato será acionado (quebra de sigilo por risco grave e atual).</p>
    </div>
    """,

    # =================================================
    # --- QUESTÕES ÉTICAS E SOCIAIS (SUAS ORIGINAIS) ---
    # =================================================
    "Posso atender de graça?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas cuide do enquadre.</h3>
        <p>O atendimento pro bono (voluntário) é permitido. O que o Código veda é usar o preço como propaganda para captar clientela de forma desleal.</p>
        <p><strong>Dica:</strong> Se for atender de graça, mantenha o mesmo rigor, horário e comprometimento do atendimento pago. O contrato terapêutico deve ser claro.</p>
    </div>
    """,

    "Posso influenciar na orientação sexual do meu paciente?": """
    <div class="resposta-humanizada">
        <h3>Não. Isso é infração ética grave.</h3>
        <p><strong>Art. 2º do Código de Ética:</strong> é vedado induzir a convicções de orientação sexual.</p>
        <p>Além disso, a Psicologia não trata orientação sexual como doença e não endossa “terapia de conversão”. O papel do psicólogo é acolher, reduzir sofrimento e fortalecer autonomia e dignidade.</p>
        <div class="alert-box warning">
            <strong>Importante:</strong> Não existe “cura gay”. Orientação sexual não é patologia e não deve ser “mudada”.
        </div>
    </div>
    """,

    "Existe psicologia evangélica?": """
    <div class="resposta-humanizada">
        <h3>Como ciência e profissão, a Psicologia é laica.</h3>
        <p>Você pode ser evangélica, mas sua prática técnica não pode ser religiosa.</p>
        <p><strong>Limites:</strong></p>
        <ul>
            <li>Você deve respeitar a fé do paciente.</li>
            <li>Você <strong>não pode</strong> usar a sessão para pregar, converter ou impor crenças.</li>
        </ul>
    </div>
    """,

    "É proíbido falar sobre religião nas sessões?": """
    <div class="resposta-humanizada">
        <h3>Não. Falar SOBRE religião pode ser necessário.</h3>
        <p>Se a fé é importante para o paciente, ela faz parte da história dele e deve ser acolhida.</p>
        <p><strong>O que é proibido:</strong> o psicólogo impor crenças, julgar com base em dogmas pessoais ou transformar a sessão em prática religiosa.</p>
    </div>
    """,

    "Posso divulgar o valor da sessão no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Pode informar, mas evite tom promocional.</h3>
        <p>Informar valores pode ser transparência. O cuidado ético é não usar “promoções”, “descontos chamativos” ou promessa de resultado como marketing.</p>
    </div>
    """,

    "Preciso de contrato para terapia online?": """
    <div class="resposta-humanizada">
        <h3>Sim, é fortemente recomendado.</h3>
        <p>Combine por escrito: sigilo, plataforma, política de faltas, o que acontece se cair a internet, formas de contato e um plano para emergências.</p>
    </div>
    """,

    # =================================================
    # --- ALIASES (para NÃO QUEBRAR botões do app) ---
    # =================================================
    "Ao dar devolutiva para os pais devo contar tudo?": """
    <div class="resposta-humanizada">
        <h3>Não. Conte apenas o estritamente essencial.</h3>
        <p>No atendimento de crianças/adolescentes, aos responsáveis comunica-se o <strong>estritamente necessário</strong> para medidas em benefício do paciente.</p>
        <p>Evite expor falas íntimas que não envolvam risco ou necessidade de proteção. Isso preserva o vínculo e o direito à privacidade.</p>
    </div>
    """,

    "Posso influenciar na orientação sexual?": """
    <div class="resposta-humanizada">
        <h3>Não. E “cura gay” não existe.</h3>
        <p>A Psicologia não trata orientação sexual como doença. Portanto, não existe “cura”.</p>
        <p>É vedado ao psicólogo induzir, pressionar ou conduzir o paciente para mudar orientação sexual. O trabalho ético é acolhimento, redução de sofrimento, fortalecimento de autonomia e enfrentamento de discriminação.</p>
    </div>
    """,

    "Posso aceitar presentes?": """
    <div class="resposta-humanizada">
        <h3>Depende do valor e do significado.</h3>
        <p>Pequenos presentes simbólicos podem ocorrer. Presentes caros ou com “cobrança” de retribuição devem ser recusados com explicação ética.</p>
    </div>
    """,

    # =================================================
    # --- BANCO NOVO (50+ respostas diretas) ---
    # =================================================

    # 1) Conversão / “cura gay”
    "Existe cura gay?": """
    <div class="resposta-humanizada">
        <h3>Não existe “cura gay”.</h3>
        <p>Orientação sexual <strong>não é doença</strong> e não é algo a ser “curado”.</p>
        <p>Práticas de “reorientação” ou “conversão” configuram violação ética: produzem culpa, vergonha e sofrimento, e não são finalidade legítima de atendimento psicológico.</p>
        <div class="alert-box warning">
            <strong>Conduta ética:</strong> acolher a pessoa, trabalhar sofrimento, fortalecer autonomia e enfrentar efeitos de discriminação e violência.
        </div>
    </div>
    """,

    "O que responder quando pedem terapia de reversão?": """
    <div class="resposta-humanizada">
        <h3>Responda com firmeza e ética.</h3>
        <p>Explique que orientação sexual não é patologia e que o psicólogo não realiza “reversão”.</p>
        <p>Você pode oferecer psicoterapia para lidar com ansiedade, culpa, conflitos familiares, violência, medo e autoaceitação — sem objetivo de mudar orientação sexual.</p>
        <div class="alert-box tip">
            💡 <strong>Frase útil:</strong> “Posso te ajudar com o sofrimento que você está vivendo, mas não com a ideia de ‘mudar’ sua orientação sexual.”
        </div>
    </div>
    """,

    # 2) Sigilo
    "Até onde vai o sigilo?": """
    <div class="resposta-humanizada">
        <h3>O sigilo é regra. Exceções são raras e justificadas.</h3>
        <p>O sigilo protege a intimidade e o vínculo terapêutico. Ele só pode ser relativizado quando há <strong>risco grave e atual</strong>, exigência legal/judicial e sempre no <strong>mínimo necessário</strong>.</p>
        <div class="alert-box tip">
            💡 Sempre que possível, converse com o paciente antes, explique limites e registre sua decisão técnica.
        </div>
    </div>
    """,

    "Até onde vai o sigilo em caso de crime?": """
    <div class="resposta-humanizada">
        <h3>Sigilo não vira “denúncia automática”.</h3>
        <p>Relatos de atos ilegais não significam, por si só, que o psicólogo deve comunicar autoridades. O foco é clínico e ético.</p>
        <p>Exceções tendem a envolver <strong>risco grave e atual</strong> a alguém (por exemplo, ameaça concreta) ou situações em que a lei imponha dever específico. Quando existir dúvida, busque orientação técnica (ex.: COF/CRP) e preserve o mínimo necessário.</p>
    </div>
    """,

    "Posso falar do caso com meu cônjuge ou amigo?": """
    <div class="resposta-humanizada">
        <h3>Não. Isso viola sigilo.</h3>
        <p>Discussão de caso deve ocorrer em contexto profissional (supervisão, equipe autorizada) e com anonimização. Conversa informal com terceiros é quebra de sigilo.</p>
    </div>
    """,

    "Posso confirmar para alguém que a pessoa é minha paciente?": """
    <div class="resposta-humanizada">
        <h3>Evite confirmar.</h3>
        <p>Confirmar que alguém é seu paciente já é informação sigilosa. A conduta mais segura é dizer que não pode confirmar nem negar por sigilo profissional.</p>
    </div>
    """,

    # 3) Rua / redes sociais / contato fora da sessão
    "Posso cumprimentar meu paciente na rua?": """
    <div class="resposta-humanizada">
        <h3>Prefira esperar o paciente.</h3>
        <p>Você pode combinar previamente: na rua, você espera o paciente cumprimentar, para proteger a privacidade.</p>
    </div>
    """,

    "Posso seguir paciente no Instagram?": """
    <div class="resposta-humanizada">
        <h3>Em geral, não é recomendado.</h3>
        <p>Seguir/ser seguida pode criar relação dual, expor intimidade e interferir no enquadre. Se houver necessidade profissional (rara), combine limites explícitos e registre o motivo.</p>
    </div>
    """,

    "Posso responder mensagens do paciente fora do horário?": """
    <div class="resposta-humanizada">
        <h3>Defina regras claras.</h3>
        <p>Atendimento não deve virar plantão informal permanente. Combine horários, canal e tipo de mensagem permitido (ex.: remarcação). Situações de crise exigem plano específico (rede de apoio e serviços adequados).</p>
    </div>
    """,

    "Posso usar WhatsApp pessoal com pacientes?": """
    <div class="resposta-humanizada">
        <h3>Pode, mas exige cautela e enquadre.</h3>
        <p>Se usar WhatsApp, deixe claro que é para logística (remarcar/confirmar). Oriente sobre privacidade do aparelho, bloqueio de tela e backups. Se possível, use número profissional.</p>
    </div>
    """,

    # 4) Relações duais
    "Posso atender amigos?": """
    <div class="resposta-humanizada">
        <h3>Evite. Se atender, precisa justificar e manejar riscos.</h3>
        <p>Atender amigos frequentemente cria relação dual, aumenta conflitos de interesse e compromete neutralidade e sigilo. O mais seguro é encaminhar.</p>
    </div>
    """,

    "Posso atender familiares?": """
    <div class="resposta-humanizada">
        <h3>Em geral, não é recomendado.</h3>
        <p>Atender familiares próximos costuma gerar conflitos de interesse e ameaça ao sigilo. Prefira encaminhar para outro profissional.</p>
    </div>
    """,

    "Posso atender o casal e um dos parceiros em terapia individual?": """
    <div class="resposta-humanizada">
        <h3>É uma zona de alto risco ético.</h3>
        <p>Isso pode gerar conflito de lealdade e percepção de parcialidade. Se ocorrer, precisa de contrato terapêutico muito claro, regras de sigilo e, muitas vezes, é melhor separar profissionais (um para o casal e outro para individual).</p>
    </div>
    """,

    "Posso atender duas pessoas da mesma família em terapia individual?": """
    <div class="resposta-humanizada">
        <h3>Possível, mas geralmente desaconselhável.</h3>
        <p>O risco é virar “juiz” do conflito, misturar confidências e comprometer o enquadre. Na dúvida, encaminhe uma das pessoas.</p>
    </div>
    """,

    # 5) Presentes e pagamentos
    "Posso receber PIX adiantado?": """
    <div class="resposta-humanizada">
        <h3>Pode, se estiver combinado.</h3>
        <p>Pagamento antecipado é uma regra contratual possível. Especifique política de remarcação, faltas e reembolso com clareza.</p>
    </div>
    """,

    "Posso cobrar multa por falta?": """
    <div class="resposta-humanizada">
        <h3>Pode, desde que esteja acordado previamente.</h3>
        <p>Política de faltas é parte do contrato terapêutico. Explique com clareza, sem constrangimento e com possibilidades de remarcação quando fizer sentido clínico.</p>
    </div>
    """,

    "Como lidar com inadimplência?": """
    <div class="resposta-humanizada">
        <h3>Com contrato, conversa e dignidade.</h3>
        <p>Evite exposição ou pressão humilhante. Relembre o acordo, proponha renegociação/encaminhamento e registre. Se houver cobrança, preserve sigilo (não exponha que é paciente).</p>
    </div>
    """,

    # 6) Documentos
    "Posso emitir declaração de comparecimento?": """
    <div class="resposta-humanizada">
        <h3>Sim.</h3>
        <p>Declaração de comparecimento é documento simples: data/horário do atendimento e identificação do profissional. Evite conteúdo clínico desnecessário.</p>
    </div>
    """,

    "Posso emitir laudo psicológico para processo?": """
    <div class="resposta-humanizada">
        <h3>Somente se você tiver finalidade, competência e método para isso.</h3>
        <p>Laudo/avaliação psicológica exige procedimento técnico específico. Psicoterapia não é automaticamente perícia. Se a demanda for judicial, considere encaminhar para avaliação com finalidade própria.</p>
    </div>
    """,

    "Posso negar um relatório solicitado?": """
    <div class="resposta-humanizada">
        <h3>Pode recusar se o pedido for inadequado ou antiético.</h3>
        <p>Você não é obrigada a produzir documento que exponha o paciente ou fuja da finalidade técnica. Ofereça alternativas: declaração de comparecimento, relatório sintético, ou orientação para avaliação apropriada.</p>
    </div>
    """,

    "O paciente pode pedir cópia do prontuário?": """
    <div class="resposta-humanizada">
        <h3>Em geral, o paciente pode solicitar acesso às informações.</h3>
        <p>Você deve avaliar a forma mais adequada: relatório, síntese ou cópia, preservando terceiros e informações que possam causar dano. Quando houver dúvida, faça relatório técnico e registre a decisão.</p>
    </div>
    """,

    # 7) Prontuário
    "Paciente pediu para não registrar no prontuário": """
    <div class="resposta-humanizada">
        <h3>Explique que o registro técnico é dever profissional.</h3>
        <p>O prontuário serve para continuidade do cuidado e proteção técnica. Você não precisa registrar detalhes íntimos desnecessários, mas precisa registrar o essencial: data, evolução, conduta e encaminhamentos.</p>
        <div class="alert-box tip">
            💡 Você pode combinar: “Vou registrar de forma sintética e sem detalhes desnecessários.”
        </div>
    </div>
    """,

    "Sou obrigada a fazer anotações?": """
    <div class="resposta-humanizada">
        <h3>Sim, é dever profissional.</h3>
        <p>O prontuário deve existir e ser guardado com sigilo. O registro não precisa ser extenso, mas deve ser técnico e suficiente.</p>
    </div>
    """,

    # 8) Online
    "Como garantir sigilo no atendimento online?": """
    <div class="resposta-humanizada">
        <h3>Combine regras e reduza riscos.</h3>
        <ul>
            <li>Oriente o paciente a estar em local privado e usar fone.</li>
            <li>Evite Wi-Fi público.</li>
            <li>Defina plataforma e um plano se a conexão cair.</li>
            <li>Tenha contato de emergência (quando aplicável).</li>
        </ul>
    </div>
    """,

    "Posso atender online com paciente em outro estado?": """
    <div class="resposta-humanizada">
        <h3>Em geral, sim, desde que regular e com cuidados.</h3>
        <p>O essencial é manter registro, contrato, sigilo, e estar em conformidade com regras profissionais vigentes para serviços psicológicos mediados por tecnologia.</p>
    </div>
    """,

    # 9) Menores
    "Posso atender adolescente sem os pais saberem?": """
    <div class="resposta-humanizada">
        <h3>Depende do contexto e das responsabilidades legais.</h3>
        <p>Na prática, pode haver situações em que o adolescente busca ajuda e a comunicação com responsáveis precisa ser manejada com cuidado. Ainda assim, é necessário avaliar segurança, consentimento, risco e o melhor interesse do adolescente.</p>
        <div class="alert-box tip">
            💡 Quando houver risco/violência, o manejo envolve rede de proteção e orientação técnica.
        </div>
    </div>
    """,

    "O que falar para os pais sobre a terapia do filho?": """
    <div class="resposta-humanizada">
        <h3>Somente o essencial.</h3>
        <p>Explique o processo, combinados, frequência e orientações gerais. Evite revelar confidências do paciente, salvo risco ou necessidade clara de proteção.</p>
    </div>
    """,

    # 10) Manejo clínico / postura
    "Posso dar conselhos diretos ao paciente?": """
    <div class="resposta-humanizada">
        <h3>Cuidado com diretividade excessiva.</h3>
        <p>Você pode oferecer reflexões, psicoeducação e hipóteses, mas evitar “mandar” o paciente fazer escolhas. O objetivo é promover autonomia, não dependência.</p>
    </div>
    """,

    "Posso confrontar o paciente?": """
    <div class="resposta-humanizada">
        <h3>Pode, se for técnico e cuidadoso.</h3>
        <p>Confronto não é agressão. Deve ter objetivo terapêutico, ser proporcional e respeitoso, evitando humilhação ou imposição moral.</p>
    </div>
    """,

    "O que fazer se eu errar com o paciente?": """
    <div class="resposta-humanizada">
        <h3>Reconheça, repare e registre.</h3>
        <p>Erros acontecem. O manejo ético é reconhecer, pedir desculpas quando couber, revisar conduta e, se necessário, encaminhar/supervisionar. Registre o essencial no prontuário.</p>
    </div>
    """,

    # 11) Publicidade
    "Posso postar depoimento de paciente?": """
    <div class="resposta-humanizada">
        <h3>Evite. É alto risco ético.</h3>
        <p>Mesmo com “autorização”, há risco de exposição, coação implícita e quebra de sigilo. Prefira divulgação educativa, sem casos identificáveis e sem promessas.</p>
    </div>
    """,

    "Posso prometer resultado na terapia?": """
    <div class="resposta-humanizada">
        <h3>Não.</h3>
        <p>Promessa de resultado é antiética e irreal. Psicoterapia envolve variáveis humanas e contextuais. Você pode explicar método, objetivo e limites.</p>
    </div>
    """,

    # 12) Encaminhamento
    "Quando devo encaminhar um paciente?": """
    <div class="resposta-humanizada">
        <h3>Quando houver limite técnico, risco ou conflito de interesse.</h3>
        <p>Encaminhe quando: você não tem competência para a demanda, há relação dual, ausência de progresso com prejuízo, ou necessidade de cuidado multiprofissional.</p>
    </div>
    """,

    "Posso atender alguém que eu já conheço socialmente?": """
    <div class="resposta-humanizada">
        <h3>Evite. Relação dual é um risco real.</h3>
        <p>Se for inevitável (cidade pequena), explicite limites, avalie riscos e registre decisão. Sempre que possível, encaminhe.</p>
    </div>
    """,

    # 13) Supervisão
    "Preciso de supervisão para atender casos complexos?": """
    <div class="resposta-humanizada">
        <h3>Não é “obrigatório”, mas é altamente recomendado.</h3>
        <p>Supervisão é medida de qualidade e segurança. Em casos de alto risco, é uma forma ética de sustentar o cuidado.</p>
    </div>
    """,

    # 14) Religião
    "Posso orar com o paciente na sessão?": """
    <div class="resposta-humanizada">
        <h3>Como técnica psicológica, não.</h3>
        <p>Se o paciente traz a fé como tema, isso pode ser acolhido clinicamente. Mas conduzir oração como intervenção pode misturar papéis e virar prática religiosa dentro de um serviço psicológico.</p>
    </div>
    """,

    # 15) Outras perguntas diretas úteis
    "Posso gravar a sessão?": """
    <div class="resposta-humanizada">
        <h3>Só com consentimento claro.</h3>
        <p>Gravação envolve risco de vazamento e exposição. Se houver gravação, combine finalidade, armazenamento seguro, tempo de guarda e quem terá acesso.</p>
    </div>
    """,

    "Posso usar IA para escrever prontuário?": """
    <div class="resposta-humanizada">
        <h3>Somente com extremo cuidado e sem expor dados.</h3>
        <p>Evite inserir dados identificáveis do paciente em ferramentas externas. Se usar IA, prefira textos genéricos, sem identificação, e revise tudo. O psicólogo segue responsável pelo conteúdo e pelo sigilo.</p>
    </div>
    """,

    "Posso atender em local público (cafeteria)?": """
    <div class="resposta-humanizada">
        <h3>Não é recomendado.</h3>
        <p>Há risco alto de quebra de sigilo, interrupções e falta de privacidade. Psicoterapia exige ambiente protegido.</p>
    </div>
    """,
}

# =====================================================
# QUICK QUESTIONS
# Prioridade: somente perguntas com resposta direta (match exato)
# e com frases curtas (melhor no mobile).
# =====================================================
QUICK_QUESTIONS = [
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
        # 1. Resetar Base
        if "load_bases" in request.form:
            clear_documents()
            index_content("Código de Ética (Resumo)", TEXTO_CODIGO_ETICA)
            flash("Cérebro ético atualizado com sucesso!", "success")
            return redirect(url_for('home'))

        # 2. Processar Pergunta
        q = request.form.get("q", "").strip()

        if q:
            # A) Match Exato (Prioridade Máxima)
            if q in RESPOSTAS_PRONTAS:
                answer = RESPOSTAS_PRONTAS[q]

            # B) Match Parcial (robusto o suficiente sem quebrar)
            else:
                found_partial = False
                q_words = set(q.lower().replace("?", "").split())

                for key, val in RESPOSTAS_PRONTAS.items():
                    key_words = set(key.lower().replace("?", "").split())
                    if not key_words:
                        continue
                    # se pelo menos 70% das palavras da chave existirem na pergunta
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
