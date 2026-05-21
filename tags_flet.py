import os
import time
import threading
import flet as ft
from pylogix import PLC

# ==============================================================================
# CONFIGURAÇÕES DO CLP E ACESSO
# ==============================================================================
IP_CLP = '172.16.35.30'
SLOT_CLP = 2
TAGS_PARA_LER = [
    'relogio[3]', 'relogio[4]', 'relogio[5]',
    'relogio[2]', 'relogio[1]', 'relogio[0]',
    'Conta[0].acc', 'Conta[1].acc',
    'Reais[0]', 'Reais[1]', 'Reais[2]',
    'Reais[3]'
]
INTERVALO_ATUALIZACAO = 0.1 
ARQUIVO_FONTE = "LCDAT&TPhoneTimeDate.ttf"

# Inicialização controlada do driver
print("Iniciando comunicação com pylogix...")
comm = PLC()
comm.IPAddress = IP_CLP
comm.ProcessorSlot = SLOT_CLP

# Histórico para os gráficos
historico_conta0 = []
historico_segundos = []
MAX_PONTOS_GRAFICO = 50

def main(page: ft.Page):
    global historico_conta0, historico_segundos
    print("Janela Flet iniciada com sucesso. Renderizando componentes...")
    
    # ----------------------------------------------------------------------
    # CARREGAMENTO SEGURO DA FONTE (Forçado Consolas caso dê erro)
    # ----------------------------------------------------------------------
    fonte_relogio = "Consolas"
    try:
        caminho_fonte = os.path.join(os.path.dirname(__file__), ARQUIVO_FONTE)
        if os.path.exists(caminho_fonte):
            page.fonts = {"LCD_Custom": caminho_fonte}
            fonte_relogio = "LCD_Custom"
            print(f"Fonte personalizada '{caminho_fonte}' carregada.")
        else:
            print(f"Aviso: Arquivo de fonte '{caminho_fonte}' não encontrado. Usando Consolas.")
    except Exception as e:
        print(f"Erro ao carregar fonte: {e}. Usando Consolas.")
        fonte_relogio = "Consolas"
    
    page.title = "Supervisório CLP - pylogix (Flet)"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 300
    page.window_height = 950
    page.padding = 20

    # --- Elementos do Cabeçalho ---
    lbl_status_conexao = ft.Container(
        content=ft.CircleAvatar(bgcolor="grey200", radius=8),
        margin=ft.margin.only(right=10)
    )
    txt_ip_clp = ft.Text(f"CLP IP: {IP_CLP}", size=14, color="lightblue", weight=ft.FontWeight.BOLD)

    # --- Painel do Relógio Digital Unificado ---
    txt_relogio_hora = ft.Text("--:--:--", font_family=fonte_relogio, size=64, color="black", text_align=ft.TextAlign.CENTER)
    txt_relogio_data = ft.Text("DATA: --/--/----", size=20, color="grey700", text_align=ft.TextAlign.CENTER)

    # --- Componentes da Tabela Dinâmica ---
    lista_tags = ['Conta[0].acc', 'Conta[1].acc'] + [f'Reais[{i}]' for i in range(4)]
    widgets_dados = {}

    linhas_tabela = []
    for tag in lista_tags:
        cor_valor = "cyan" if "Reais" in tag else "orange"
        
        txt_tag_nome = ft.Text(tag, size=14, color="bluegrey200", weight=ft.FontWeight.W_500)
        txt_tag_valor = ft.Text("---", font_family=fonte_relogio, size=20, color=cor_valor, text_align=ft.TextAlign.CENTER)
        led_tag_status = ft.CircleAvatar(bgcolor="grey800", radius=6)
        
        widgets_dados[tag.lower()] = {
            "valor": txt_tag_valor,
            "led": led_tag_status
        }

        linhas_tabela.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Container(content=txt_tag_nome, alignment=ft.alignment.center_left)),
                    ft.DataCell(ft.Container(content=txt_tag_valor, alignment=ft.alignment.center, expand=True)),
                    ft.DataCell(ft.Container(content=led_tag_status, alignment=ft.alignment.center)),
                ]
            )
        )

    tabela_variaveis = ft.DataTable(
        heading_row_color="bluegrey900",
        data_row_min_height=40,
        columns=[
            ft.DataColumn(ft.Text("TAG", weight=ft.FontWeight.BOLD, color="white")),
            ft.DataColumn(ft.Text("VALOR", weight=ft.FontWeight.BOLD, color="white"), numeric=True),
            ft.DataColumn(ft.Text("STATUS", weight=ft.FontWeight.BOLD, color="white")),
        ],
        rows=linhas_tabela,
        expand=True
    )

    # ----------------------------------------------------------------------
    # CONSTRUÇÃO DO GRÁFICO
    # ----------------------------------------------------------------------
    chart_data_conta0 = ft.LineChartData(
        data_points=[],
        stroke_width=2,
        color="orange",
        curved=False
    )
    
    chart_data_segundos = ft.LineChartData(
        data_points=[],
        stroke_width=2,
        color="cyan",
        curved=False
    )

    grafico_tendencia = ft.LineChart(
        data_series=[chart_data_conta0, chart_data_segundos],
        border=ft.Border(bottom=ft.BorderSide(1, "white"), left=ft.BorderSide(1, "white")),
        left_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=v, label=ft.Text(str(v), size=10)) for v in [0, 15, 30, 45, 60]], labels_size=30),
        bottom_axis=ft.ChartAxis(show_labels=False),
        min_y=0,
        max_y=60,
        min_x=0,
        max_x=MAX_PONTOS_GRAFICO - 1,
        expand=True
    )

    # --- Evento de Zerar Contadores ---
    def zerar_contadores(e):
        btn_zerar.disabled = True
        btn_zerar.text = "A ESCREVER NO CLP..."
        page.update()
        try:
            res0 = comm.Write('Conta[0].acc', 0)
            res1 = comm.Write('Conta[1].acc', 0)
            if res0 and res1 and res0.Status == "Success" and res1.Status == "Success":
                txt_ip_clp.value = f"CLP IP: {IP_CLP} - CONTADORES ZERADOS OK!"
                txt_ip_clp.color = "greenaccent400"
                historico_conta0.clear()
            else:
                txt_ip_clp.value = f"CLP IP: {IP_CLP} - FALHA AO ZERAR (PROIBIDO)"
                txt_ip_clp.color = "red"
        except Exception as err:
            txt_ip_clp.value = f"CLP IP: {IP_CLP} - ERRO DE ESCRITA"
            txt_ip_clp.color = "red"
            print(f"Erro na escrita do CLP: {err}")
        
        page.update()
        time.sleep(1.5)
        btn_zerar.disabled = False
        btn_zerar.text = "ZERAR CONTADORES (CONTA[0] E CONTA[1])"
        txt_ip_clp.value = f"CLP IP: {IP_CLP}"
        txt_ip_clp.color = "lightblue"
        page.update()

    btn_zerar = ft.ElevatedButton(
        text="ZERAR CONTADORES (CONTA[0] E [1])",
        bgcolor="orange700",
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)),
        on_click=zerar_contadores
    )

    painel_grafico_estilizado = ft.Container(
        content=ft.Column([
            ft.Text(" 📊 TENDÊNCIA ( Laranja: Conta| Ciano: Segundos ) ", 
                    size=12, color="grey400", weight=ft.FontWeight.BOLD),
            ft.Container(content=grafico_tendencia, padding=10, height=220)
        ], spacing=5),
        border=ft.border.all(1, "grey800"),
        border_radius=8,
        padding=10,
    )

    # --- Estrutura de Layout da Página ---
    page.add(
        ft.Row([
            ft.Text("MONITORAMENTO EM TEMPO REAL", size=18, weight=ft.FontWeight.BOLD, color="greenaccent400"),
        ], alignment=ft.MainAxisAlignment.START),
        
        ft.Row([
            txt_ip_clp, 
            lbl_status_conexao
        ], alignment=ft.MainAxisAlignment.END),
        
        ft.Container(
            content=ft.Column([txt_relogio_hora, txt_relogio_data], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            bgcolor="grey950",
            padding=5,
            border_radius=8,
            border=ft.border.all(1, "grey800"),
            alignment=ft.alignment.center
        ),
        
        ft.Container(
            content=ft.Column([tabela_variaveis], scroll=ft.ScrollMode.ADAPTIVE),
            height=350,
            border_radius=8,
            border=ft.border.all(1, "grey800")
        ),
        
        ft.Row([btn_zerar], alignment=ft.MainAxisAlignment.CENTER),
        painel_grafico_estilizado
    )

    # --- Thread de Comunicação em Background ---
    def loop_atualizacao_dados():
        print("Thread de leitura iniciada...")
        heartbeat = False
        time.sleep(1) # Aguarda a interface carregar completamente
        
        while True:
            sucesso_comunicacao = False
            valores_lidos = {}
            
            try:
                retorno = comm.Read(TAGS_PARA_LER)
                if retorno and isinstance(retorno, list) and len(retorno) > 0:
                    sucesso_comunicacao = True
                    for resposta in retorno:
                        if hasattr(resposta, 'Status') and resposta.Status == "Success":
                            valores_lidos[resposta.TagName.lower()] = resposta.Value
                        else:
                            sucesso_comunicacao = False
                else:
                    sucesso_comunicacao = False
            except Exception as thread_err:
                print(f"Erro crítico na thread de leitura do CLP: {thread_err}")
                sucesso_comunicacao = False

            try:
                if sucesso_comunicacao:
                    lbl_status_conexao.content.bgcolor = "green" if heartbeat else "greenaccent700"
                    heartbeat = not heartbeat

                    try:
                        hora = valores_lidos.get('relogio[3]', 0)
                        minuto = valores_lidos.get('relogio[4]', 0)
                        segundo = valores_lidos.get('relogio[5]', 0)
                        dia = valores_lidos.get('relogio[2]', 1)
                        mes = valores_lidos.get('relogio[1]', 1)
                        ano = valores_lidos.get('relogio[0]', 2026)
                        
                        txt_relogio_hora.value = f"{hora:02d}:{minuto:02d}:{segundo:02d}"
                        txt_relogio_data.value = f"DATA: {dia:02d}/{mes:02d}/{ano:04d}"
                        
                        historico_segundos.append(segundo)
                        if len(historico_segundos) > MAX_PONTOS_GRAFICO:
                            historico_segundos.pop(0)
                    except Exception:
                        pass

                    for resposta in retorno:
                        if hasattr(resposta, 'TagName'):
                            tag_low = resposta.TagName.lower()
                            if tag_low in widgets_dados:
                                w = widgets_dados[tag_low]
                                if resposta.Status == "Success":
                                    valor_formatado = f"{resposta.Value:.2f}" if isinstance(resposta.Value, float) else str(resposta.Value)
                                    w["valor"].value = valor_formatado
                                    w["led"].bgcolor = "greenaccent400"
                                    
                                    if tag_low == "conta[0].acc":
                                        historico_conta0.append(resposta.Value)
                                        if len(historico_conta0) > MAX_PONTOS_GRAFICO:
                                            historico_conta0.pop(0)
                                else:
                                    w["valor"].value = "---"
                                    w["led"].bgcolor = "red800"

                    chart_data_conta0.data_points = [ft.LineChartDataPoint(x, y) for x, y in enumerate(historico_conta0)]
                    chart_data_segundos.data_points = [ft.LineChartDataPoint(x, y) for x, y in enumerate(historico_segundos)]

                else:
                    lbl_status_conexao.content.bgcolor = "red"
                    txt_relogio_hora.value = "--:--:--"
                    txt_relogio_data.value = "DATA: --/--/----"
                    for tag_low, w in widgets_dados.items():
                        w["valor"].value = "---"
                        w["led"].bgcolor = "red800"
                    
                    chart_data_conta0.data_points = []
                    chart_data_segundos.data_points = []

                page.update()
            except Exception as update_err:
                print(f"Erro ao atualizar interface: {update_err}")

            time.sleep(INTERVALO_ATUALIZACAO)

    # Inicialização Segura da Thread
    thread = threading.Thread(target=loop_atualizacao_dados, daemon=True)
    thread.start()

    def encerrar_comunicacao(e):
        if e.data == "close":
            print("Fechando conexão com o CLP...")
            try:
                comm.Close()
            except Exception:
                pass
            page.window_destroy()
            
    page.on_window_event = encerrar_comunicacao

if __name__ == "__main__":
    # Executa em modo Desktop nativo
    ft.app(target=main)