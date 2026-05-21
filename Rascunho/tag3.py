import tkinter as tk
from tkinter import font as tkfont
from pylogix import PLC

# ==============================================================================
# CONFIGURAÇÕES DO CLP E ACESSO
# ==============================================================================
IP_CLP = '172.16.35.30'
SLOT_CLP = 2
TAGS_PARA_LER = [
    'relogio[3]',
    'relogio[4]',
    'relogio[5]',
    'relogio[2]',
    'relogio[1]',
    'relogio[0]',
    'Conta[0].acc',
    'Conta[1].acc'
]
INTERVALO_ATUALIZACAO = 500  # Tempo em milissegundos (100ms = 10Hz)

# ==============================================================================
# CLASSE PRINCIPAL DA CLASSE VISUAL (GUI)
# ==============================================================================
class MonitorCLPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Supervisório CLP - pylogix")
        self.root.geometry("650x350")
        self.root.configure(bg="#1e1e1e")  # Fundo grafite escuro (estilo industrial)

        # ----------------------------------------------------------------------
        # SELEÇÃO DE FONTES CUSTOMIZADAS
        # ----------------------------------------------------------------------
        self.fonte_titulo = tkfont.Font(family="Consolas", size=12, weight="bold")
        self.fonte_cabecalho = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.fonte_dados = tkfont.Font(family="Digital-7", size=18, weight="normal")

        # Inicializa o driver do pylogix
        self.comm = PLC()
        self.comm.IPAddress = IP_CLP
        self.comm.ProcessorSlot = SLOT_CLP

        # Dicionário para guardar as referências dos textos na tela e atualizá-los
        self.widgets_dados = {}

        # Configura a interface e os eventos
        self.criar_layout()
        self.root.bind("<Escape>", self.fechar_aplicativo)  # Vincula o ESC para fechar
        
        # Inicia o ciclo de leitura em segundo plano
        self.atualizar_dados()

    def criar_layout(self):
        """Monta a estrutura visual da tabela na janela."""
        # Título Superior
        lbl_titulo = tk.Label(
            self.root, 
            text=f"MONITORAMENTO EM TEMPO REAL - CLP ({IP_CLP})", 
            font=self.fonte_titulo, fg="#00ff66", bg="#1e1e1e"
        )
        lbl_titulo.pack(pady=15)

        # Container principal da tabela
        tabela_frame = tk.Frame(self.root, bg="#1e1e1e")
        tabela_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        # Configura as larguras proporcionais das 3 colunas (Grid)
        tabela_frame.columnconfigure(0, weight=2)  # TagName ganha mais espaço
        tabela_frame.columnconfigure(1, weight=1)  # Value
        tabela_frame.columnconfigure(2, weight=1)  # Status

        # Cabeçalhos da Tabela (Corrigido: padding removido e trocado por ipady no grid)
        cabecalhos = ["TagName", "Value", "Status"]
        for col_idx, texto in enumerate(cabecalhos):
            lbl = tk.Label(
                tabela_frame, text=texto, font=self.fonte_cabecalho, 
                fg="#ffffff", bg="#2d2d2d", relief=tk.FLAT
            )
            # ipady adiciona o espaçamento interno vertical na célula do grid
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=2, ipady=5)

        # Cria as linhas de dados dinâmicas vazias
        for row_idx, tag in enumerate(TAGS_PARA_LER, start=1):
            # Cor alternada para as linhas (Efeito zebrado)
            cor_fundo = "#252526" if row_idx % 2 == 0 else "#2d2d2d"

            # Coluna 1: Nome da Tag (Corrigido: padding removido)
            lbl_name = tk.Label(tabela_frame, text=tag, font=self.fonte_dados, fg="#9cdcfe", bg=cor_fundo, anchor="w")
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1, ipadx=5, ipady=3)

            # Coluna 2: Valor (Dinâmico)
            lbl_value = tk.Label(tabela_frame, text="---", font=self.fonte_dados, fg="#b5cea8", bg=cor_fundo, anchor="center")
            lbl_value.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)

            # Coluna 3: Status (Dinâmico)
            lbl_status = tk.Label(tabela_frame, text="---", font=self.fonte_dados, fg="#ce9178", bg=cor_fundo, anchor="center")
            lbl_status.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)

            # Salva a referência dos Labels dinâmicos para atualização posterior
            self.widgets_dados[tag] = {
                "value_widget": lbl_value,
                "status_widget": lbl_status
            }

        # Rodapé com instrução
        lbl_rodape = tk.Label(
            self.root, text="Pressione [ESC] para encerrar o aplicativo", 
            font=tkfont.Font(family="Consolas", size=9, slant="italic"), fg="#888888", bg="#1e1e1e"
        )
        lbl_rodape.pack(pady=10)

    def atualizar_dados(self):
        """Busca os valores no CLP e atualiza a interface de forma assíncrona."""
        try:
            # Faz a leitura das tags via pylogix
            resultados = self.comm.Read(TAGS_PARA_LER)
            
            for resultado in resultados:
                tag = resultado.TagName
                if tag in self.widgets_dados:
                    # Converte e atualiza o valor na tela
                    valor_texto = str(resultado.Value) if resultado.Value is not None else "N/A"
                    self.widgets_dados[tag]["value_widget"].config(text=valor_texto)
                    
                    # Atualiza o status e altera a cor do texto dependendo do sucesso
                    status_texto = str(resultado.Status)
                    self.widgets_dados[tag]["status_widget"].config(text=status_texto)
                    
                    if status_texto == "Success":
                        self.widgets_dados[tag]["status_widget"].config(fg="#4ec9b0")
                    else:
                        self.widgets_dados[tag]["status_widget"].config(fg="#f44336") # Vermelho se houver erro
                        
        except Exception as e:
            print(f"Erro na comunicação: {e}")

        # Agenda a execução desta mesma função após o intervalo de tempo escolhido
        self.loop_id = self.root.after(INTERVALO_ATUALIZACAO, self.atualizar_dados)

    def fechar_aplicativo(self, event=None):
        """Fecha as conexões e destrói a janela de forma segura."""
        print("\nFechando aplicação visual...")
        self.root.after_cancel(self.loop_id) # Para o loop de atualização do Tkinter
        self.comm.Close()                    # Fecha o canal Ethernet/IP com o CLP
        self.root.destroy()                  # Encerra a janela de vez

# ==============================================================================
# EXECUÇÃO DO PROGRAMA
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorCLPApp(root)
    root.mainloop()

