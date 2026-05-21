import os
import time
import threading
import flet as ft
from pylogix import PLC

# ==============================================================================
# CONFIGURAÇÕES & CONSTANTES
# ==============================================================================
IP_PADRAO = "172.16.35.30"
SLOT_PADRAO = 2
INTERVALO_ATUALIZACAO = 0.1
MAX_PONTOS_GRAFICO = 50
ARQUIVO_FONTE = "LCDAT&TPhoneTimeDate.ttf"
ARQUIVO_TAGS_TABELA = "tags_tabela.txt"
ARQUIVO_TAGS_GRAFICO = "tags_grafico.txt"

# Cores para o gráfico (ciclo automático)
CORES_GRAFICO = ["orange", "cyan", "green", "purple", "red", "blue", "teal", "amber"]

# ==============================================================================
# GERENCIAMENTO DE ESTADO & CONEXÃO
# ==============================================================================
class EstadoPLC:
    def __init__(self):
        self.lock = threading.Lock()
        self.comm = PLC()
        self.ip = IP_PADRAO
        self.slot = SLOT_PADRAO
        self.conectado = False

    def conectar(self, ip: str, slot: int = 2) -> bool:
        with self.lock:
            try:
                if self.conectado:
                    try: self.comm.Close()
                    except: pass
                self.comm.IPAddress = ip
                self.comm.ProcessorSlot = slot
                self.comm.Open()
                self.ip = ip
                self.slot = slot
                self.conectado = True
                return True
            except Exception as e:
                print(f"❌ Falha ao conectar: {e}")
                self.conectado = False
                return False

    def desconectar(self) -> None:
        with self.lock:
            try: self.comm.Close()
            except: pass
            self.conectado = False

estado = EstadoPLC()

# ==============================================================================
# LEITURA DE ARQUIVOS TXT
# ==============================================================================
def carregar_tags_txt(caminho: str, fallback: list[str]) -> list[str]:
    try:
        if os.path.exists(caminho):
            with open(caminho, 'r', encoding='utf-8') as f:
                tags = [t.strip().strip('"').strip("'") for t in f.read().split(',') if t.strip()]
            return tags if tags else fallback
        print(f"⚠️ Arquivo '{caminho}' não encontrado. Usando lista padrão.")
        return fallback
    except Exception as e:
        print(f"❌ Erro ao ler {caminho}: {e}")
        return fallback

TAGS_TABELA_PADRAO = ['Conta[0].acc', 'Conta[1].acc'] + [f'Reais[{i}]' for i in range(6)]
TAGS_GRAFICO_PADRAO = ['Conta[0].acc', 'relogio[5]']

tags_tabela = carregar_tags_txt(ARQUIVO_TAGS_TABELA, TAGS_TABELA_PADRAO)
tags_grafico = carregar_tags_txt(ARQUIVO_TAGS_GRAFICO, TAGS_GRAFICO_PADRAO)

# Tags para leitura única no CLP (união sem duplicatas)
TAGS_LEITURA = list(dict.fromkeys(
    tags_tabela + tags_grafico + [
        'relogio[0]', 'relogio[1]', 'relogio[2]', 
        'relogio[3]', 'relogio[4]', 'relogio[5]'
    ]
))

# Estruturas de dados
historicos_grafico = {tag: [] for tag in tags_grafico}
widgets_dados = {}
series_grafico = {}

# ==============================================================================
# APLICAÇÃO FLET
# ==============================================================================
def main(page: ft.Page):
    page.title = "Supervisório CLP - pylogix (Flet)"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 350
    page.window_height = 980

    # --- Carregamento de Fonte ---
    fonte_relogio = "Consolas"
    try:
        if os.path.exists(ARQUIVO_FONTE):
            page.fonts = {"LCD_Custom": ARQUIVO_FONTE}
            fonte_relogio = "LCD_Custom"
            print(f"✅ Fonte '{ARQUIVO_FONTE}' carregada.")
        else:
            print("⚠️ Fonte personalizada não encontrada. Usando Consolas.")
    except Exception as e:
        print(f"❌ Erro ao carregar fonte: {e}")
        fonte_relogio = "Consolas"

    # --- Elementos da Tabela ---
    linhas_tabela = []
    for tag in tags_tabela:
        cor_valor = "cyan" if "Reais" in tag else "orange"
        txt_nome = ft.Text(tag, size=14, color="bluegrey200", weight=ft.FontWeight.W_500)
        txt_valor = ft.Text("---", font_family=fonte_relogio, size=20, color=cor_valor, text_align=ft.TextAlign.CENTER)
        led = ft.CircleAvatar(bgcolor="grey800", radius=6)
        widgets_dados[tag.lower()] = {"valor": txt_valor, "led": led}
        linhas_tabela.append(ft.DataRow(cells=[
            ft.DataCell(ft.Container(txt_nome, alignment=ft.alignment.center_left)),
            ft.DataCell(ft.Container(txt_valor, alignment=ft.alignment.center, expand=True)),
            ft.DataCell(ft.Container(led, alignment=ft.alignment.center)),
        ]))

    tabela_variaveis = ft.DataTable(
        heading_row_color="bluegrey900", data_row_min_height=40, expand=True,
        columns=[ft.DataColumn(ft.Text("TAG", weight=ft.FontWeight.BOLD, color="white")),
                 ft.DataColumn(ft.Text("VALOR", weight=ft.FontWeight.BOLD, color="white"), numeric=True),
                 ft.DataColumn(ft.Text("STATUS", weight=ft.FontWeight.BOLD, color="white"))],
        rows=linhas_tabela
    )

    # --- Elementos do Gráfico (Dashboard) ---
    for i, tag in enumerate(tags_grafico):
        cor = CORES_GRAFICO[i % len(CORES_GRAFICO)]
        series_grafico[tag] = ft.LineChartData(data_points=[], stroke_width=2, color=cor, curved=False)

    grafico_tendencia = ft.LineChart(
        data_series=list(series_grafico.values()),
        border=ft.Border(bottom=ft.BorderSide(1, "white"), left=ft.BorderSide(1, "white")),
        left_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=v, label=ft.Text(str(v), size=10)) for v in [0, 15, 30, 45, 60]], labels_size=30),
        bottom_axis=ft.ChartAxis(show_labels=False),
        min_y=0, max_y=60, min_x=0, max_x=MAX_PONTOS_GRAFICO - 1,
        expand=True
    )

    legenda_grafico = " | ".join([f"{tags_grafico[i]} ({CORES_GRAFICO[i % len(CORES_GRAFICO)]})" for i in range(len(tags_grafico))])

    # --- Controles de Conexão ---
    txt_ip = ft.TextField(label="IP do CLP", value=estado.ip, width=200, hint_text="192.168.x.x")
    lbl_status = ft.Container(content=ft.CircleAvatar(bgcolor="grey200", radius=8), margin=ft.margin.only(right=10))
    btn_conectar = ft.ElevatedButton("Conectar", bgcolor="green700", color="white")
    btn_desconectar = ft.ElevatedButton("Desconectar", bgcolor="red700", color="white", disabled=True)
    txt_status_msg = ft.Text("Status: Aguardando conexão...", size=12, color="grey500")

    def on_conectar(e):
        ip = txt_ip.value.strip()
        if not ip: return
        btn_conectar.disabled = True
        btn_conectar.text = "Conectando..."
        page.update()
        sucesso = estado.conectar(ip, SLOT_PADRAO)
        btn_conectar.disabled = False
        btn_conectar.text = "Conectar"
        btn_desconectar.disabled = not sucesso
        lbl_status.content.bgcolor = "green" if sucesso else "red"
        txt_status_msg.value = f"Status: {'Conectado' if sucesso else 'Falha na conexão'} ({ip})"
        page.update()

    def on_desconectar(e):
        estado.desconectar()
        btn_desconectar.disabled = True
        lbl_status.content.bgcolor = "grey200"
        txt_status_msg.value = "Status: Desconectado"
        page.update()

    btn_conectar.on_click = on_conectar
    btn_desconectar.on_click = on_desconectar

    # --- Relógio ---
    txt_relogio_hora = ft.Text("--:--:--", font_family=fonte_relogio, size=56, color="black", text_align=ft.TextAlign.CENTER)
    txt_relogio_data = ft.Text("DATA: --/--/----", size=18, color="grey700", text_align=ft.TextAlign.CENTER)

    # --- Botão Zerar ---
    def zerar_contadores(e):
        btn_zerar.disabled = True
        btn_zerar.text = "A ESCREVER NO CLP..."
        page.update()
        try:
            with estado.lock:
                if not estado.conectado:
                    raise ConnectionError("CLP não está conectado.")
                res0 = estado.comm.Write('Conta[0].acc', 0)
                res1 = estado.comm.Write('Conta[1].acc', 0)
            if res0 and res1 and res0.Status == "Success" and res1.Status == "Success":
                txt_status_msg.value = "✅ Contadores zerados com sucesso!"
                txt_status_msg.color = "greenaccent400"
                historicos_grafico.get('Conta[0].acc', []).clear()
            else:
                txt_status_msg.value = "❌ Falha ao zerar (Permissão/Tag bloqueada)"
                txt_status_msg.color = "red"
        except Exception as err:
            txt_status_msg.value = f"❌ Erro: {err}"
            txt_status_msg.color = "red"
            print(f"Erro na escrita: {err}")
        
        page.update()
        time.sleep(1.2)
        btn_zerar.disabled = False
        btn_zerar.text = "ZERAR CONTADORES (CONTA[0] E [1])"
        txt_status_msg.value = "Status: Aguardando..."
        txt_status_msg.color = "grey500"
        page.update()

    btn_zerar = ft.ElevatedButton(
        text="ZERAR CONTADORES (CONTA[0] E [1])",
        bgcolor="orange700", color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)),
        on_click=zerar_contadores
    )

    # --- Navegação / Views ---
    def abrir_dashboard(e):
        page.route = "/dashboard"

    def fechar_dashboard(e):
        page.route = "/"

    # View Principal
    view_main = ft.View(
        "/",
        [
            ft.Row([ft.Text("🌐 SUPERVISÓRIO CLP", size=18, weight=ft.FontWeight.BOLD, color="greenaccent400")]),
            ft.Row([txt_ip, btn_conectar, btn_desconectar, lbl_status]),
            txt_status_msg,
            ft.Container(
                content=ft.Column([txt_relogio_hora, txt_relogio_data], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="grey950", padding=15, border_radius=8, border=ft.border.all(1, "grey800"), alignment=ft.alignment.center
            ),
            ft.Container(content=ft.Column([tabela_variaveis], scroll=ft.ScrollMode.ADAPTIVE), height=320, border_radius=8, border=ft.border.all(1, "grey800")),
            ft.Row([btn_zerar], alignment=ft.MainAxisAlignment.CENTER),
            ft.ElevatedButton("📊 ABRIR DASHBOARD DE TENDÊNCIAS", icon="show_chart", on_click=abrir_dashboard, expand=True)
        ]
    )

    # View Dashboard
    view_dashboard = ft.View(
        "/dashboard",
        [
            ft.Row([
                ft.IconButton("arrow_back", on_click=fechar_dashboard, tooltip="Voltar"),
                ft.Text("📈 TENDÊNCIA EM TEMPO REAL", size=18, weight=ft.FontWeight.BOLD, color="cyan"),
                ft.Container(expand=True)
            ]),
            ft.Text(legenda_grafico, size=12, color="grey400", text_align=ft.TextAlign.CENTER),
            ft.Container(content=grafico_tendencia, padding=10, height=400, border=ft.border.all(1, "grey800"), border_radius=8, expand=True)
        ]
    )

    page.views.clear()
    page.views.append(view_main)
    page.update()

    def on_route_change(e):
        page.views.clear()
        if page.route == "/":
            page.views.append(view_main)
        elif page.route == "/dashboard":
            page.views.append(view_dashboard)
        page.update()

    page.on_route_change = on_route_change

    # ==============================================================================
    # THREAD DE ATUALIZAÇÃO
    # ==============================================================================
    def loop_atualizacao():
        print("🔄 Thread de leitura iniciada.")
        time.sleep(0.5)
        while True:
            if not estado.conectado:
                time.sleep(INTERVALO_ATUALIZACAO)
                continue

            try:
                with estado.lock:
                    retorno = estado.comm.Read(TAGS_LEITURA)
                
                if not retorno or not isinstance(retorno, list):
                    raise ValueError("Resposta inválida do CLP")

                # Mapeamento rápido tag -> valor
                valores = {}
                for r in retorno:
                    if hasattr(r, 'Status') and r.Status == "Success":
                        valores[r.TagName.lower()] = r.Value

                # Atualiza Relógio
                h = valores.get('relogio[3]', 0)
                m = valores.get('relogio[4]', 0)
                s = valores.get('relogio[5]', 0)
                d = valores.get('relogio[2]', 1)
                mo = valores.get('relogio[1]', 1)
                a = valores.get('relogio[0]', 2026)
                txt_relogio_hora.value = f"{h:02d}:{m:02d}:{s:02d}"
                txt_relogio_data.value = f"DATA: {d:02d}/{mo:02d}/{a:04d}"

                # Atualiza Tabela
                for tag_nome, w in widgets_dados.items():
                    if tag_nome in valores:
                        val = valores[tag_nome]
                        w["valor"].value = f"{val:.2f}" if isinstance(val, float) else str(val)
                        w["led"].bgcolor = "greenaccent400"
                    else:
                        w["valor"].value = "---"
                        w["led"].bgcolor = "red800"

                # Atualiza Gráfico
                for tag in tags_grafico:
                    tag_low = tag.lower()
                    if tag_low in valores:
                        historicos_grafico[tag].append(valores[tag_low])
                        if len(historicos_grafico[tag]) > MAX_PONTOS_GRAFICO:
                            historicos_grafico[tag].pop(0)
                        series_grafico[tag].data_points = [
                            ft.LineChartDataPoint(x, y) for x, y in enumerate(historicos_grafico[tag])
                        ]
                    else:
                        series_grafico[tag].data_points = []

                lbl_status.content.bgcolor = "green"
                page.update()

            except Exception as e:
                lbl_status.content.bgcolor = "red"
                print(f"⚠️ Erro na leitura: {e}")
                # Limpa UI em caso de falha
                txt_relogio_hora.value = "--:--:--"
                txt_relogio_data.value = "DATA: --/--/----"
                for w in widgets_dados.values():
                    w["valor"].value = "---"
                    w["led"].bgcolor = "red800"
                for s in series_grafico.values():
                    s.data_points = []
                page.update()

            time.sleep(INTERVALO_ATUALIZACAO)

    threading.Thread(target=loop_atualizacao, daemon=True).start()

    def on_close(e):
        if e.data == "close":
            print("🔌 Encerrando comunicação e fechando app...")
            estado.desconectar()
            page.window_destroy()

    page.on_window_event = on_close

if __name__ == "__main__":
    ft.app(target=main)