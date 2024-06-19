import cv2
import numpy as np
import mediapipe as mp
import random
import time

# Inicializa a captura de vídeo
captura_video = cv2.VideoCapture(0)

# # # # # # # # # # # # # # # # # # # # # # # # # MEDIA PIPE # # # # # # # # # # # # # # # # # # # # # # # # #
# Inicializa o MediaPipe para a detecção de mãos
mp_maos = mp.solutions.hands
# Pode detectar 1 mão apenas com confiança > 75%
maos = mp_maos.Hands(max_num_hands=1, min_detection_confidence=0.75)
mp_desenho = mp.solutions.drawing_utils


# # # # # # # # # # # # # # # # # # # # # # # # # TELA # # # # # # # # # # # # # # # # # # # # # # # # #
# Inicializa uma tela branca para desenhar
canvas = np.ones((480, 640, 3), dtype="uint8") * 255
# Coordenadas iniciais
prev_x, prev_y = None, None
coordenadas_desenhadas = []

# # # # # # # # # # # # # # # # # # # # # # # # # BOTÕES # # # # # # # # # # # # # # # # # # # # # # # # #
tempo_botao_pressionado = None
tempo_max_botao_pressionado = 2 # Segundos
mao_estava_sobre_botao_nova_forma = False

# Botão limpar
botao_limpar_top_left = (10, 10)  # Posição superior esquerda do botão
botao_limpar_bottom_right = (110, 110)  # Posição inferior direita do botão
botao_limpar_cor = (0, 0, 255)  # Cor do botão (vermelho)

# Botão submit
botao_submit_top_left = (530, 10)
botao_submit_bottom_right = (630, 110)
botao_submit_cor = (255, 0, 0)

# Botão novo desenho
botao_novo_desenho_top_left = (290, 10)
botao_novo_desenho_bottom_right = (390, 110)
botao_novo_desenho_cor = (0, 255, 0)

# # # # # # # # # # # # # # # # # # # # # # # # # FORMAS # # # # # # # # # # # # # # # # # # # # # # # # # 
# Variável para a forma geométrica sorteada
formas = ["circulo", "quadrado"]
forma_atual = random.choice(formas)
acuracia_verificada = False
grossura_desenho = 5

# # # # # # # # # # # # # # # # # # # # # # # # # FUNÇÕES # # # # # # # # # # # # # # # # # # # # # # # # # 

def verifica_acuracia(forma, coordenadas):
    # Criando um canvas vazio
    canvas_desenho = np.ones((480, 640, 3), dtype="uint8") * 255 

    # Redesenhando no canvas_desenho a forma desenhada através das cordenadas
    for i in range(1, len(coordenadas)):
        cv2.line(img=canvas_desenho, pt1=coordenadas[i-1], pt2=coordenadas[i], color=(0,0,0), thickness=5)

    #Para verificar o que foi desenhado no novo canvas
    #path = 'canvas.jpg'
    #cv2.imwrite(path, canvas_desenho)

    # Convertendo a forma desenhada para tons de cinza
    gray = cv2.cvtColor(src=canvas_desenho, code=cv2.COLOR_BGR2GRAY)
    # Aplicando limiarização
    _, limiarizado = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    # Encontrando contornos
    contornos, _ = cv2.findContours(limiarizado, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Se 0 não houve desenho
    if len(contornos) == 0:
        return 0.0
    
    # Considerando apenas o maior contorno
    maior_contorno = max(contornos, key=cv2.contourArea)

    # Aproximando o contorno a um polígono
    epsilon = 0.02 * cv2.arcLength(curve=maior_contorno, closed=True)
    aproximacao = cv2.approxPolyDP(curve=maior_contorno, epsilon=epsilon, closed=True)

    if forma == "circulo":
        area = cv2.contourArea(contour=maior_contorno)
        perimetro = cv2.arcLength(curve=maior_contorno, closed=True)
        circularidade = 4 * np.pi * (area / (perimetro * perimetro))
        similaridade = abs(min(1, circularidade) * 100) # Similaridade baseada na circularidade
    elif forma == "quadrado":
        (x, y, w, h) = cv2.boundingRect(array=aproximacao)
        proporcao = float(w) / h
        similaridade = abs((1 - abs(1 - proporcao)) * 100)# Similaridade baseada na proporção da figura
    else:
        similaridade = 0.0

    return similaridade

# Função para verificar se a mão está sobre um botão
def is_mao_sobre_botao(marcacoes_mao, frame_width, frame_height, top_left, bottom_right):
    for marcacao in marcacoes_mao:
        x = int(marcacao.x * frame_width)
        y = int(marcacao.y * frame_height)

        # Verifica se x e y está sobreposto sobre o botão
        if top_left[0] <= x <=bottom_right[0] and top_left[1] <= y <= bottom_right[1]:
            return True
        
    return False

# Função para evitar desenhar a qualquer momento
def is_dedo_colado_ao_polegar(marcacoes, frame_width, frame_height, threshold=30):
    ponta_dedo_indicador = marcacoes[8]
    ponta_dedo_polegar =  marcacoes[4]

    indicador_x = int(ponta_dedo_indicador.x * frame_width)
    indicador_y = int(ponta_dedo_indicador.y * frame_height)
    polegar_x = int(ponta_dedo_polegar.x * frame_width)
    polegar_y = int(ponta_dedo_polegar.y * frame_height)

    distancia = np.sqrt((indicador_x - polegar_x)**2 + (indicador_y - polegar_y)**2) 

    return distancia < threshold


def desenha_texto(canvas, text, location, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, font_thickness=2, padding=10, background_color=(0, 0, 0), text_color=(255, 255, 255)):
    # Calcula o tamanho do texto
    text_size, baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
    text_width, text_height = text_size
    
    # Calcula a posição do retângulo
    rect_top_left = (location[0], location[1])
    rect_bottom_right = (location[0] + text_width + 2 * padding, location[1] + text_height + 2 * padding)
    
    # Desenha o retângulo de fundo
    cv2.rectangle(canvas, rect_top_left, rect_bottom_right, background_color, -1)
    
    # Desenha o texto
    cv2.putText(canvas, text, (location[0] + padding, location[1] + text_height + padding), font, font_scale, text_color, font_thickness, cv2.LINE_AA)


while captura_video.isOpened():
    sucesso, frame = captura_video.read()

    if not sucesso:
        break
    
    # Flipando a imagem da camera, que por default está invertida
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Para identificar as mãos 
    resultado = maos.process(frame_rgb)

    mao_sobre_botao_limpar = False
    mao_sobre_botao_submit = False
    mao_sobre_botao_nova_forma = False

    # Verifica se há pontos de uma mão detectados
    if resultado.multi_hand_landmarks:
        # Pra cada ponto ponto da mão
        for marcacoes_mao in resultado.multi_hand_landmarks:
            #Verifica se o dedo indicador não está colado ao polegar  
            if not is_dedo_colado_ao_polegar(marcacoes_mao.landmark, frame.shape[1], frame.shape[0]):
                # x e y coordenadas do dedo indicador
                x = int(marcacoes_mao.landmark[8].x * frame.shape[1])
                y = int(marcacoes_mao.landmark[8].y * frame.shape[0])

                # Verifica se já existe um ponto de inicio para o desenho
                if prev_x is not None and prev_y is not None:
                    cv2.line(canvas, (prev_x, prev_y), (x,y), (0, 0, 0), grossura_desenho)
                    coordenadas_desenhadas.append((prev_x, prev_y))
                prev_x, prev_y = x, y

            else: #Indicador colado ao polegar, não desenhar nada
                prev_x, prev_y = None, None
            
            # Verifica se a mão está sobre alguns dos botões
            if is_mao_sobre_botao(marcacoes_mao.landmark, frame.shape[1], frame.shape[0], botao_limpar_top_left, botao_limpar_bottom_right):
                mao_sobre_botao_limpar = True
            
            if is_mao_sobre_botao(marcacoes_mao.landmark, frame.shape[1], frame.shape[0], botao_submit_top_left, botao_submit_bottom_right):
                mao_sobre_botao_submit = True

            if is_mao_sobre_botao(marcacoes_mao.landmark, frame.shape[1], frame.shape[0], botao_novo_desenho_top_left, botao_novo_desenho_bottom_right):
                mao_sobre_botao_nova_forma = True

            # Desenha os pontos detectados da mão
            mp_desenho.draw_landmarks(frame, marcacoes_mao, mp_maos.HAND_CONNECTIONS)
    else: # Nenhuma mão detectada
        prev_x, prev_y = None, None

    # Se a mão está sobre o botão de limpar, devemos contar por quanto tempo está pressionado, se
    # for maior que o tempo definido, limpar a tela.
    if mao_sobre_botao_limpar:
        if tempo_botao_pressionado is None:
            tempo_botao_pressionado = time.time()
        tempo_decorrido = time.time() - tempo_botao_pressionado

        if tempo_decorrido >= tempo_max_botao_pressionado:
            canvas = np.ones((480, 640, 3), dtype="uint8") * 255
            acuracia_verificada = False
            tempo_botao_pressionado = None
    else:
        tempo_botao_pressionado = None

    # Se a mão tiver sobre o botão de submit, devemos verificar a acurácia do desenho
    if mao_sobre_botao_submit and not acuracia_verificada:
        acuracia = verifica_acuracia(forma_atual, coordenadas_desenhadas)
        text_location = (330, 400)
        texto = f"Acuracia: {acuracia:.2f}%"
        desenha_texto(canvas, texto, text_location)
        acuracia_verificada = True
    
    # Escolher nova forma
    if mao_sobre_botao_nova_forma and not mao_estava_sobre_botao_nova_forma:

        # Escolher de maneira aleatória uma forma diferente da atual
        nova_forma = random.choice(formas)
        while nova_forma == forma_atual:
            nova_forma = random.choice(formas)
        forma_atual = nova_forma
        canvas = np.ones((480, 640, 3), dtype="uint8") * 255
        coordenadas_desenhadas = []
        acuracia_verificada = False
    
    mao_estava_sobre_botao_nova_forma = mao_sobre_botao_nova_forma

    # Desenhando os botões de limpar, novo desenho e submeter
    cv2.rectangle(canvas, botao_limpar_top_left, botao_limpar_bottom_right, botao_limpar_cor, -1)
    cv2.rectangle(canvas, botao_novo_desenho_top_left, botao_novo_desenho_bottom_right, botao_novo_desenho_cor, -1)
    cv2.rectangle(canvas, botao_submit_top_left, botao_submit_bottom_right, botao_submit_cor, -1)

    # Desenhar um timer para limpar o desenho, a fim de guiar o usuário
    if tempo_botao_pressionado is not None:
        elapsed_time = time.time() - tempo_botao_pressionado
        angle = int((elapsed_time / tempo_max_botao_pressionado) * 360)
        center = ((botao_limpar_top_left[0] + botao_limpar_bottom_right[0]) // 2, (botao_limpar_top_left[1] + botao_limpar_bottom_right[1]) // 2)
        radius = (botao_limpar_bottom_right[0] - botao_limpar_top_left[0]) // 3
        cv2.ellipse(canvas, center, (radius, radius), 0, 0, angle, (0, 255, 0), 5)
    

    text = f"Draw: {forma_atual}"
    canvas_height, canvas_width = canvas.shape[:2]
    text_location = (25, 400)

    # Chama a função para desenhar o texto centrado
    desenha_texto(canvas, text, text_location)

    # Mostra o canvas e o frame da câmera na mesma tela
    combined = cv2.addWeighted(frame, 0.7, canvas, 0.5, 0)
    cv2.imshow("Frame", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

captura_video.release()
cv2.destroyAllWindows()