import os
import sys
import ctypes
import tkinter as tk
from tkinter import font as tkfont
from pylogix import PLC

# ==============================================================================
# FUNÇÃO PARA CARREGAR FONTE EM TEMPO DE EXECUÇÃO (SEM INSTALAR NO WINDOWS)
# ==============================================================================
def carregar_fonte_local(caminho_fonte):
    """Carrega temporariamente um arquivo .ttf na memória do Windows para o script usar."""
    if sys.platform == "win32":
        if os.path.exists(caminho_fonte):
            # Códigos da API do Windows para adicionar recursos de fonte
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

# Nome do arquivo que deve estar na mesma pasta
ARQUIVO_FONTE = "digital-7.ttf" 
# Nome interno que a fonte assume após ser carregada no sistema
NOME_INTERNO_FONTE = "Digital-7" 

# Tenta carregar a fonte antes de iniciar a interface gráfica
carregar_fonte_local(ARQUIVO_FONTE)

# ==============================================================================
# CLASSE PRINCIPAL DA CLASSE VISUAL (GUI)
# ==============================================================================
class MonitorCLPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Supervisório CLP - pylogix")
        self.root.geometry("650x350")
        self.root.configure(bg="#1e1e1e")  # Fundo grafite escuro

        # ----------------------------------------------------------------------
        # SELEÇÃO DE FONTES CUSTOMIZADAS
        # ----------------------------------------------------------------------
        self.fonte_titulo = tkfont.Font(family="Consolas", size=18, weight="bold")
        self.fonte_cabecalho = tkfont.Font(family="Consolas", size=12, weight="bold")
        self.fonte_dados = tkfont.Font(family="Consolas", size=12, weight="normal")
        
        # Define a fonte LCD carregada localmente para a coluna de valores
        self.fonte_lcd = tkfont.Font(family=NOME_INTERNO_FONTE, size=26, weight="bold")

        # Inicializa o driver do pylogix
        self.comm = PLC()
        self.comm.IPAddress = IP_CLP
        self.comm.ProcessorSlot = SLOT_CLP

        self.widgets_dados = {}
        self.criar_layout()
        self.root.bind("<Escape>", self.fechar_aplicativo)
        self.atualizar_dados()

    def criar_layout(self):
        """Monta a estrutura visual da tabela na janela."""
        lbl_titulo = tk.Label(
            self.root, 
            text=f"MONITORAMENTO EM TEMPO REAL - CLP ({IP_CLP})", 
            font=self.fonte_titulo, fg="#00ff66", bg="#1e1e1e"
        )
        lbl_titulo.pack(pady=15)

        tabela_frame = tk.Frame(self.root, bg="#1e1e1e")
        tabela_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        tabela_frame.columnconfigure(0, weight=2)
        tabela_frame.columnconfigure(1, weight=1)
        tabela_frame.columnconfigure(2, weight=1)

        cabecalhos = ["TagName", "Value", "Status"]
        for col_idx, texto in enumerate(cabecalhos):
            lbl = tk.Label(
                tabela_frame, text=texto, font=self.fonte_cabecalho, 
                fg="#ffffff", bg="#2d2d2d", relief=tk.FLAT
            )
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=2, ipady=5)

        for row_idx, tag in enumerate(TAGS_PARA_LER, start=1):
            cor_fundo = "#252526" if row_idx % 2 == 0 else "#2d2d2d"

            # Coluna 1: Nome da Tag
            lbl_name = tk.Label(tabela_frame, text=tag, font=self.fonte_dados, fg="#9cdcfe", bg=cor_fundo, anchor="w")
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1, ipadx=5, ipady=5)

            # Coluna 2: Valor (Configurado com estilo LCD e cor âmbar industrial)
            lbl_value = tk.Label(
                tabela_frame, text="---", font=self.fonte_lcd, 
                fg="#ff9900", bg=cor_fundo, anchor="center"
            )
            lbl_value.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)

            # Coluna 3: Status
            lbl_status = tk.Label(tabela_frame, text="---", font=self.fonte_dados, fg="#ce9178", bg=cor_fundo, anchor="center")
            lbl_status.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)

            self.widgets_dados[tag] = {
                "value_widget": lbl_value,
                "status_widget": lbl_status
            }

        lbl_rodape = tk.Label(
            self.root, text="Pressione [ESC] para encerrar o aplicativo", 
            font=tkfont.Font(family="Consolas", size=9, slant="italic"), fg="#888888", bg="#1e1e1e"
        )
        lbl_rodape.pack(pady=10)

    def atualizar_dados(self):
        """Busca os valores no CLP e atualiza a interface."""
        try:
            resultados = self.comm.Read(TAGS_PARA_LER)
            
            for resultado in resultados:
                tag = resultado.TagName
                if tag in self.widgets_dados:
                    valor_texto = str(resultado.Value) if resultado.Value is not None else "N/A"
                    self.widgets_dados[tag]["value_widget"].config(text=valor_texto)
                    
                    status_texto = str(resultado.Status)
                    self.widgets_dados[tag]["status_widget"].config(text=status_texto)
                    
                    if status_texto == "Success":
                        self.widgets_dados[tag]["status_widget"].config(fg="#4ec9b0")
                    else:
                        self.widgets_dados[tag]["status_widget"].config(fg="#f44336")
                        
        except Exception as e:
            print(f"Erro na comunicação: {e}")

        self.loop_id = self.root.after(INTERVALO_ATUALIZACAO, self.atualizar_dados)

    def fechar_aplicativo(self, event=None):
        """Fecha as conexões e destrói a janela."""
        print("\nFechando aplicação visual...")
        self.root.after_cancel(self.loop_id)
        self.comm.Close()
        self.root.destroy()

# ==============================================================================
# EXECUÇÃO DO PROGRAMA
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorCLPApp(root)
    root.mainloop()
