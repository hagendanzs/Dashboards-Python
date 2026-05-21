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
    'Conta[1].acc',
    'Reais[0]',
    'Reais[1]',
    'Reais[2]',
    'Reais[3]',
    'Reais[4]',
    'Reais[5]'
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
        self.root.geometry("750x880") # Ajustado levemente para a nova linha de título
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
        self.historico_conta0 = []    
        self.historico_segundos = []  
        self.max_pontos_grafico = 50  

        self.widgets_dados = {}
        self.criar_layout()
        self.root.bind("<Escape>", self.fechar_aplicativo)
        self.atualizar_dados()

    def criar_layout(self):
        """Monta a estrutura visual da tabela, relógio, indicador e gráfico."""
        # Frame Principal do Topo (Container para as duas linhas)
        topo_frame = tk.Frame(self.root, bg="#1e1e1e")
        topo_frame.pack(padx=20, pady=10, fill=tk.X)

        # LINHA 1: Título Principal Solitário
        lbl_titulo = tk.Label(
            topo_frame, 
            text="MONITORAMENTO EM TEMPO REAL", 
            font=self.fonte_titulo, fg="#00ff66", bg="#1e1e1e"
        )
        lbl_titulo.pack(anchor="w", pady=(0, 5))

        # LINHA 2: Frame Secundário para IP e Status da Comunicação
        sub_topo_frame = tk.Frame(topo_frame, bg="#1e1e1e")
        sub_topo_frame.pack(fill=tk.X)

        # Informação do IP do CLP alinhada à esquerda
        lbl_ip_info = tk.Label(
            sub_topo_frame, 
            text=f"CLP IP: {IP_CLP}", 
            font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e"
        )
        lbl_ip_info.pack(side=tk.LEFT)

        # Elementos do LED empurrados para o lado direito da linha 2
        self.canvas_led = tk.Canvas(sub_topo_frame, width=25, height=25, bg="#1e1e1e", bd=0, highlightthickness=0)
        self.canvas_led.pack(side=tk.RIGHT, padx=(5, 0))
        self.led_id = self.canvas_led.create_oval(3, 3, 22, 22, fill="#444444", outline="#666666")

        lbl_led_texto = tk.Label(sub_topo_frame, text="COM STATUS:", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e")
        lbl_led_texto.pack(side=tk.RIGHT)

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
        # PAINEL DAS VARIÁVEIS (TABELA DINÂMICA)
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

        tags_exibicao = ['Conta.acc', 'Conta.acc'] + [f'Reais[{i}]' for i in range(6)]
        
        for row_idx, tag in enumerate(tags_exibicao, start=1):
            cor_fundo = "#252526" if row_idx % 2 == 0 else "#2d2d2d"

            lbl_name = tk.Label(frame_tabela, text=tag, font=self.fonte_dados, fg="#9cdcfe", bg=cor_fundo, anchor="w")
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1, ipadx=5, ipady=4)

            cor_valores = "#00ffff" if "Reais" in tag else "#ff9900"
            lbl_value = tk.Label(frame_tabela, text="---", font=self.fonte_lcd_media, fg=cor_valores, bg=cor_fundo, anchor="center")
            lbl_value.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)

            lbl_status = tk.Label(frame_tabela, text="---", font=self.fonte_dados, fg="#ce9178", bg=cor_fundo, anchor="center")
            lbl_status.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)

            self.widgets_dados[tag.lower()] = {
                "value_widget": lbl_value,
                "status_widget": lbl_status
            }

        # ----------------------------------------------------------------------
        # PAINEL DO HISTÓRICO GRÁFICO (Canvas Real-Time Multitendência)
        # ----------------------------------------------------------------------
        frame_grafico = tk.LabelFrame(self.root, text=" TENDÊNCIA EM TEMPO REAL ( Laranja: Conta.acc | Ciano: Segundos ) ", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e", bd=1, relief=tk.SOLID)
        frame_grafico.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        self.canvas_grafico = tk.Canvas(frame_grafico, bg="#111111", highlightthickness=0)
        self.canvas_grafico.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        lbl_rodape = tk.Label(self.root, text="Pressione ESC para sair", font=self.fonte_dados, fg="#555555", bg="#1e1e1e")
        lbl_rodape.pack(side=tk.BOTTOM, pady=5)

    def atualizar_dados(self):
        """Executa a leitura em lote no CLP, processa valores decimais, relógio e atualiza a tela."""
        try:
            retornos = self.comm.Read(TAGS_PARA_LER)
            dados = {}
            comunicacao_ok = True
            
            for r in retornos:
                if r.Status == 'Success':
                    dados[r.TagName.lower()] = r.Value
                else:
                    comunicacao_ok = False

            if retornos and comunicacao_ok:
                self.heartbeat_state = not self.heartbeat_state
                cor_led = "#00ff66" if self.heartbeat_state else "#009933"
                self.canvas_led.itemconfig(self.led_id, fill=cor_led, outline="#00ff66")

                hora = dados.get('relogio', 0)
                minuto = dados.get('relogio', 0)
                segundo = dados.get('relogio', 0)
                dia = dados.get('relogio', 0)
                mes = dados.get('relogio', 0)
                ano = dados.get('relogio', 0)

                self.lbl_relogio_hora.config(text=f"{hora:02d}:{minuto:02d}:{segundo:02d}")
                self.lbl_relogio_data.config(text=f"DATA: {dia:02d}/{mes:02d}/{ano:04d}")

                self.historico_segundos.append(int(segundo))

                for tag_mapeada, widgets in self.widgets_dados.items():
                    if tag_mapeada in dados:
                        valor_puro = dados[tag_mapeada]
                        
                        if "reais" in tag_mapeada:
                            try:
                                valor_exibido = f"{float(valor_puro):.2f}"
                            except (ValueError, TypeError):
                                valor_exibido = str(valor_puro)
                        else:
                            valor_exibido = str(valor_puro)

                        widgets["value_widget"].config(text=valor_exibido)
                        widgets["status_widget"].config(text="OK", fg="#00ff66")
                        
                        if tag_mapeada == 'conta.acc':
                            self.historico_conta0.append(int(valor_puro))
                    else:
                        widgets["value_widget"].config(text="---")
                        widgets["status_widget"].config(text="Erro Tag", fg="#ff3333")

                self.desenhar_grafico()
            else:
                self.marcar_como_offline()

        except Exception as e:
            print(f"Erro na execução do loop: {e}")
            self.marcar_como_offline()

        self.root.after(INTERVALO_ATUALIZACAO, self.atualizar_dados)

    def marcar_como_offline(self):
        """Modifica a interface para alertar falha de conexão com o CLP."""
        self.canvas_led.itemconfig(self.led_id, fill="#ff3333", outline="#990000")
        self.lbl_relogio_hora.config(text="--:--:--")
        self.lbl_relogio_data.config(text="DATA: --/--/----")
        for widgets in self.widgets_dados.values():
            widgets["value_widget"].config(text="---")
            widgets["status_widget"].config(text="Offline", fg="#ff3333")

    def desenhar_grafico(self):
        """Plota as duas tendências históricas (Conta e Segundos) de forma normalizada."""
        self.canvas_grafico.delete("all")
        largura = self.canvas_grafico.winfo_width()
        altura = self.canvas_grafico.winfo_height()

        if largura <= 10 or altura <= 10:
            return

        if len(self.historico_conta0) > self.max_pontos_grafico:
            self.historico_conta0.pop(0)
        if len(self.historico_segundos) > self.max_pontos_grafico:
            self.historico_segundos.pop(0)

        ponto_passo = largura / (self.max_pontos_grafico - 1)

        # PENA 1: Conta.acc (Cor: Laranja)
        if len(self.historico_conta0) >= 2:
            min_v = min(self.historico_conta0)
            max_v = max(self.historico_conta0)
            range_v = max_v - min_v if max_v != min_v else 100

            pontos_c0 = []
            for i, val in enumerate(self.historico_conta0):
                x = i * ponto_passo
                y = altura - 15 - ((val - min_v) / range_v) * (altura - 30)
                pontos_c0.append((x, y))

            for i in range(len(pontos_c0) - 1):
                x1, y1 = pontos_c0[i]
                x2, y2 = pontos_c0[i+1]
                self.canvas_grafico.create_line(x1, y1, x2, y2, fill="#ff9900", width=2)

        # PENA 2: Segundos (Cor: Ciano - Escala Fixa de Tempo 0-59)
        if len(self.historico_segundos) >= 2:
            min_s, max_s = 0, 59
            range_s = max_s - min_s

            pontos_seg = []
            for i, val in enumerate(self.historico_segundos):
                x = i * ponto_passo
                y = altura - 15 - ((val - min_s) / range_s) * (altura - 30)
                pontos_seg.append((x, y))

            for i in range(len(pontos_seg) - 1):
                x1, y1 = pontos_seg[i]
                x2, y2 = pontos_seg[i+1]
                self.canvas_grafico.create_line(x1, y1, x2, y2, fill="#00ffff", width=2, dash=(4, 2))

    def fechar_aplicativo(self, event=None):
        self.comm.Close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorCLPApp(root)
    root.mainloop()
