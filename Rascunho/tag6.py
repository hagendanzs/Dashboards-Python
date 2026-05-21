import os
import sys
import ctypes
import tkinter as tk
from tkinter import font as tkfont
from pylogix import PLC

#===============================================================================
# ENGIE OPERAÇÃO E MANUTENÇÃO
# PROGRAMADO POR GEOVANE FERRAZ MONTEIRO, 18/05/2026 
# PROIBIDA A DISTRIBUIÇÃO SEM AVISO PRÉVIO E CONCENTIMENTO
# ==============================================================================
# FUNÇÃO PARA CARREGAR FONTE EM TEMPO DE EXECUÇÃO (SEM INSTALAR NO WINDOWS)
# ==============================================================================
def carregar_fonte_local(caminho_fonte):
    """Carrega temporariamente um arquivo .ttf na memória do Windows para o script usar."""
    if sys.platform == "win32":
        if os.path.exists(caminho_fonte):
            FR_PRIVATE = 0x10
            retorno = ctypes.windll.gdi32.AddFontResourceExW(caminho_fonte, FR_PRIVATE, 0)
            if retorno != 0:
                print(f"Font carregada com sucesso a partir de: {caminho_fonte}")
                return True
            else:
                print("Falha ao registrar a fonte via API do Windows.")
        else:
            print(f"Aviso: Arquivo de fonte '{caminho_fonte}' não foi encontrado na pasta.")
    else:
        print("Carregamento dinâmico automático configurado apenas para Windows.")
    return False

# ==============================================================================
# CONFIGURAÇÕES DO CLP E ACESSO
# ==============================================================================
IP_CLP = '172.16.35.30'
SLOT_CLP = 2

TAGS_PARA_LER = [
    'relogio[3]',  # Hora
    'relogio[4]',  # Minuto
    'relogio[5]',  # Segundo
    'relogio[2]',  # Dia
    'relogio[1]',  # Mês
    'relogio[0]',  # Ano
    'Conta[0].acc',
    'Conta[1].acc'
]
INTERVALO_ATUALIZACAO = 500  # Tempo em milissegundos (500ms = 2Hz)

ARQUIVO_FONTE = "LCDAT&TPhoneTimeDate.ttf" 
NOME_INTERNO_FONTE = "LCD AT&T Phone Time/Date" 

carregar_fonte_local(ARQUIVO_FONTE)

# ==============================================================================
# CLASSE PRINCIPAL DA CLASSE VISUAL (GUI)
# ==============================================================================
class MonitorCLPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Supervisório CLP - pylogix")
        self.root.geometry("750x700")  # Aumentado para acomodar o gráfico
        self.root.configure(bg="#1e1e1e")

        # ----------------------------------------------------------------------
        # SELEÇÃO DE FONTES CUSTOMIZADAS
        # ----------------------------------------------------------------------
        self.fonte_titulo = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.fonte_cabecalho = tkfont.Font(family="Consolas", size=11, weight="bold")
        self.fonte_dados = tkfont.Font(family="Consolas", size=11, weight="normal")
        self.fonte_lcd_grande = tkfont.Font(family=NOME_INTERNO_FONTE, size=48, weight="bold")
        self.fonte_lcd_media = tkfont.Font(family=NOME_INTERNO_FONTE, size=20, weight="bold")

        # Inicializa o driver do pylogix
        self.comm = PLC()
        self.comm.IPAddress = IP_CLP
        self.comm.ProcessorSlot = SLOT_CLP

        # Variáveis de controle para o Indicador (Heartbeat) e Histórico
        self.heartbeat_state = False
        self.historico_valores = []  # Armazena os últimos pontos do gráfico
        self.max_pontos_grafico = 50 # Quantidade máxima de pontos na tela

        self.widgets_contadores = {}
        self.criar_layout()
        self.root.bind("<Escape>", self.fechar_aplicativo)
        self.atualizar_dados()

    def criar_layout(self):
        """Monta a estrutura visual da tabela, relógio, indicador e gráfico."""
        # Topo Frame (Título + Indicador de Comunicação)
        topo_frame = tk.Frame(self.root, bg="#1e1e1e")
        topo_frame.pack(padx=20, pady=10, fill=tk.X)

        lbl_titulo = tk.Label(
            topo_frame, 
            text=f"MONITORAMENTO EM TEMPO REAL - CLP ({IP_CLP})", 
            font=self.fonte_titulo, fg="#00ff66", bg="#1e1e1e"
        )
        lbl_titulo.pack(side=tk.LEFT, pady=5)

        # Container do Indicador Luminoso (Led)
        self.canvas_led = tk.Canvas(topo_frame, width=25, height=25, bg="#1e1e1e", bd=0, highlightthickness=0)
        self.canvas_led.pack(side=tk.RIGHT, padx=10, pady=5)
        # Desenha o círculo do LED desativado inicialmente
        self.led_id = self.canvas_led.create_oval(3, 3, 22, 22, fill="#444444", outline="#666666")

        lbl_led_texto = tk.Label(topo_frame, text="COM:", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e")
        lbl_led_texto.pack(side=tk.RIGHT, pady=5)

        # ----------------------------------------------------------------------
        # PAINEL DO RELÓGIO DIGITAL UNIFICADO
        # ----------------------------------------------------------------------
        frame_relogio = tk.LabelFrame(self.root, text=" HORÁRIO DO CLP ", font=self.fonte_cabecalho, fg="#ffffff", bg="#151515", bd=2, relief=tk.GROOVE)
        frame_relogio.pack(padx=20, pady=5, fill=tk.X)

        self.lbl_relogio_hora = tk.Label(frame_relogio, text="--:--:--", font=self.fonte_lcd_grande, fg="#00ffff", bg="#151515")
        self.lbl_relogio_hora.pack(pady=2)

        self.lbl_relogio_data = tk.Label(frame_relogio, text="DATA: --/--/----", font=self.fonte_dados, fg="#888888", bg="#151515")
        self.lbl_relogio_data.pack(pady=2)

        # ----------------------------------------------------------------------
        # PAINEL DOS CONTADORES (TABELA)
        # ----------------------------------------------------------------------
        frame_tabela = tk.LabelFrame(self.root, text=" VARIÁVEIS DE PROCESSO ", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e", bd=0)
        frame_tabela.pack(padx=20, pady=5, fill=tk.X)

        frame_tabela.columnconfigure(0, weight=2)
        frame_tabela.columnconfigure(1, weight=1)
        frame_tabela.columnconfigure(2, weight=1)

        cabecalhos = ["TagName", "Value", "Status"]
        for col_idx, texto in enumerate(cabecalhos):
            lbl = tk.Label(
                frame_tabela, text=texto, font=self.fonte_cabecalho, 
                fg="#ffffff", bg="#2d2d2d", relief=tk.FLAT
            )
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=2, ipady=4)

        tags_contadores = ['conta[0].acc', 'conta[1].acc']
        for row_idx, tag in enumerate(tags_contadores, start=1):
            cor_fundo = "#252526" if row_idx % 2 == 0 else "#2d2d2d"

            lbl_name = tk.Label(frame_tabela, text=tag, font=self.fonte_dados, fg="#9cdcfe", bg=cor_fundo, anchor="w")
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1, ipadx=5, ipady=4)

            lbl_value = tk.Label(frame_tabela, text="---", font=self.fonte_lcd_media, fg="#ff9900", bg=cor_fundo, anchor="center")
            lbl_value.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)

            lbl_status = tk.Label(frame_tabela, text="---", font=self.fonte_dados, fg="#ce9178", bg=cor_fundo, anchor="center")
            lbl_status.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)

            self.widgets_contadores[tag] = {
                "value_widget": lbl_value,
                "status_widget": lbl_status
            }

        # ----------------------------------------------------------------------
        # PAINEL DO HISTÓRICO GRÁFICO (Canvas Real-Time)
        # ----------------------------------------------------------------------
        frame_grafico = tk.LabelFrame(self.root, text=" TENDÊNCIA EM TEMPO REAL (Conta[0].acc) ", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e", bd=1, relief=tk.SOLID)
        frame_grafico.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        # Canvas onde a linha será desenhada dinamicamente
        self.canvas_grafico = tk.Canvas(frame_grafico, bg="#111111", highlightthickness=0)
        self.canvas_grafico.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Rodapé
        lbl_rodape = tk.Label(
            self.root, text="Pressione [ESC] para encerrar o aplicativo", 
            font=tkfont.Font(family="Consolas", size=9, slant="italic"), fg="#888888", bg="#1e1e1e"
        )
        lbl_rodape.pack(pady=5)

    def desenhar_grafico(self):
        """Redesenha a linha de tendência com base no histórico armazenado."""
        self.canvas_grafico.delete("linha_tendencia") # Limpa a linha anterior
        
        if len(self.historico_valores) < 2:
            return

        # Captura as dimensões atuais da tela do gráfico de forma responsiva
        largura = self.canvas_grafico.winfo_width()
        altura = self.canvas_grafico.winfo_height()

        # Evita divisão por zero caso o componente ainda esteja renderizando
        if largura <= 1 or altura <= 1:
            return

        # Escalonamento dinâmico baseado no maior e menor valor do histórico
        max_val = max(self.historico_valores)
        min_val = min(self.historico_valores)
        amplitude = max_val - min_val
        if amplitude == 0: 
            amplitude = 1  # Evita divisão por zero se o valor for constante

        # Calcula o espaçamento horizontal entre os pontos do gráfico
        passo_x = largura / (self.max_pontos_grafico - 1)
        pontos_coordenadas = []

        for idx, valor in enumerate(self.historico_valores):
            # Calcula o X (da esquerda para a direita)
            x = idx * passo_x
            # Calcula o Y (Invertido, pois no Canvas o topo é 0. Margem de 15px interna)
            y = altura - 15 - ((valor - min_val) / amplitude) * (altura - 30)
            pontos_coordenadas.append((x, y))

        # Desenha as linhas conectando os pontos calculados
        for i in range(len(pontos_coordenadas) - 1):
            x1, y1 = pontos_coordenadas[i]
            x2, y2 = pontos_coordenadas[i+1]
            self.canvas_grafico.create_line(
                x1, y1, x2, y2, 
                fill="#00ff66", width=2, tags="linha_tendencia"
            )

    def atualizar_dados(self):
        """Busca os valores no CLP, altera o estado do LED de comunicação e plota o gráfico."""
        comunicacao_sucesso = False
        try:
            resultados = self.comm.Read(TAGS_PARA_LER)
            if not isinstance(resultados, list):
                resultados = [resultados]

            valores_clp = {}
            status_clp = {}
            for r in resultados:
                if r.TagName:
                    nome_limpo = r.TagName.lower()
                    valores_clp[nome_limpo] = r.Value
                    status_clp[nome_limpo] = r.Status

            # --- PROCESSAMENTO DO RELÓGIO ---
            ano = valores_clp.get('relogio[0]', 0)
            mes = valores_clp.get('relogio[1]', 0)
            dia = valores_clp.get('relogio[2]', 0)
            hora = valores_clp.get('relogio[3]', 0)
            minuto = valores_clp.get('relogio[4]', 0)
            segundo = valores_clp.get('relogio[5]', 0)

            if status_clp.get('relogio[3]') == "Success" and hora is not None:
                string_hora = f"{hora:02d}:{minuto:02d}:{segundo:02d}"
                string_data = f"DATA DO SISTEMA: {dia:02d}/{mes:02d}/{ano}"
                self.lbl_relogio_hora.config(text=string_hora, fg="#00ffff")
                self.lbl_relogio_data.config(text=string_data)
                comunicacao_sucesso = True
            else:
                self.lbl_relogio_hora.config(text="CHAL-ERR", fg="#f44336")
                self.lbl_relogio_data.config(text="FALHA AO LER RELÓGIO")

            # --- ATUALIZAÇÃO DOS CONTADORES E HISTÓRICO ---
            for tag_alvo, widgets in self.widgets_contadores.items():
                if tag_alvo in valores_clp:
                    val = valores_clp[tag_alvo]
                    stat = status_clp[tag_alvo]

                    valor_texto = str(val) if val is not None else "N/A"
                    widgets["value_widget"].config(text=valor_texto)
                    widgets["status_widget"].config(text=stat)

                    if stat == "Success":
                        widgets["status_widget"].config(fg="#4ec9b0")
                        # Alimenta o gráfico especificamente com o valor da tag Conta[0].acc
                        if tag_alvo == 'conta[0].acc' and val is not None:
                            self.historico_valores.append(float(val))
                            # Mantém apenas os últimos N pontos para não estourar a memória
                            if len(self.historico_valores) > self.max_pontos_grafico:
                                self.historico_valores.pop(0)
                    else:
                        widgets["status_widget"].config(fg="#f44336")

            # Redesenha a linha de tendência com os novos dados incluídos
            self.desenhar_grafico()

        except Exception as e:
            print(f"Erro na comunicação do loop: {e}")

        # --- LÓGICA DO LED DE COMUNICAÇÃO (HEARTBEAT) ---
        if comunicacao_sucesso:
            # Alterna o estado do boolean a cada ciclo (pisca-pisca)
            self.heartbeat_state = not self.heartbeat_state
            cor_led = "#00ff66" if self.heartbeat_state else "#005522" # Verde claro vs Verde escuro
        else:
            cor_led = "#f44336" # Vermelho fixo caso perca totalmente a conexão

        self.canvas_led.itemconfig(self.led_id, fill=cor_led)

        # Executa o próximo ciclo
        self.loop_id = self.root.after(INTERVALO_ATUALIZACAO, self.atualizar_dados)

    def fechar_aplicativo(self, event=None):
        """Fecha as conexões e destrói a janela de forma segura."""
        print("\nFechando aplicação visual...")
        try:
            self.root.after_cancel(self.loop_id)
        except Exception:
            pass
        self.comm.Close()
        self.root.destroy()

# ==============================================================================
# EXECUÇÃO DO PROGRAMA
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorCLPApp(root)
    root.mainloop()
