import paramiko
import time
import threading
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES DE ACESSO AO SERVIDOR LINUX (ASH/BUSYBOX)
# ==============================================================================
SSH_HOST = "172.16.35.2" 
SSH_USER = "root" 
SSH_PASS = "h4rdFlip" 

# Configuração de escala para o gráfico de rede (Ex: 10 MB/s equivale a 100% da barra)
REDE_MAX_VELOCIDADE_MBS = 10.0 

# Variáveis globais para calcular a velocidade da rede
g_bytes_in_ant = 0.0
g_bytes_out_ant = 0.0
g_tempo_ant = 0.0
ULTIMO_ERRO = "Iniciando conexão..."

def obter_metricas_servidor(ssh):
    """Executa e extrai todas as métricas cruas de forma isolada e segura"""
    global ULTIMO_ERRO
    try:
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat | grep '^cpu '")
        cpu1_linha = stdout.readline().strip().split()
        
        time.sleep(0.5) 
        
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat | grep '^cpu '")
        cpu2_linha = stdout.readline().strip().split()
        
        comando_demais = (
            "cat /proc/sys/kernel/hostname ; "
            "cat /proc/meminfo | grep -E 'MemTotal|MemAvailable|MemFree' | awk '{print $2}' | tr '\\n' '|' ; echo ; "
            "df -h / | awk 'NR==2 {print $5}' || df -h / | awk 'NR==3 {print $4}' ; "
            "interface=$(ip route | grep default | awk '{print $5}') ; "
            "cat /proc/net/dev | grep \"$interface\" | awk '{print $2\"|\"$10}'"
        )
        
        stdin, stdout, stderr = ssh.exec_command(comando_demais)
        linhas_bloco = [l.strip() for item in stdout.readlines() if (l := item.strip())]
        
        if len(linhas_bloco) < 4:
            ULTIMO_ERRO = "Resposta incompleta do servidor nas métricas."
            return None

        uso_cpu = 0.0
        if cpu1_linha and cpu2_linha and cpu1_linha[0] == 'cpu' and cpu2_linha[0] == 'cpu':
            c1_v = [int(x) for x in cpu1_linha[1:]]
            c2_v = [int(x) for x in cpu2_linha[1:]]
            diff_total = sum(c2_v) - sum(c1_v)
            diff_idle = c2_v[3] - c1_v[3]
            if diff_total > 0:
                uso_cpu = round((1.0 - (diff_idle / diff_total)) * 100, 2)

        hostname = linhas_bloco[0]
        dados_mem = linhas_bloco[1].split('|')
        mem_total = float(dados_mem[0])
        mem_livre = float(dados_mem[1]) if len(dados_mem) > 2 and dados_mem[1] else float(dados_mem[2])
        perc_mem = round(((mem_total - mem_livre) / mem_total) * 100, 2)
        tam_memoria = f"{mem_total / (1024**2):.2f} GB"

        perc_disco = float(linhas_bloco[2].replace('%', ''))
        bytes_in_raw, bytes_out_raw = linhas_bloco[3].split('|')
        
        return {
            "hostname": hostname,
            "uso_cpu": uso_cpu,
            "uso_memoria": perc_mem,
            "tam_memoria": tam_memoria,
            "perc_disco": perc_disco,
            "bytes_in": float(bytes_in_raw),
            "bytes_out": float(bytes_out_raw)
        }
    except Exception as e:
        ULTIMO_ERRO = f"Erro na coleta: {e}"
        return None

def coletar_dados_com_velocidade():
    global g_bytes_in_ant, g_bytes_out_ant, g_tempo_ant, ULTIMO_ERRO
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=3)
        res = obter_metricas_servidor(ssh)
        
        if not res:
            return None
        
        tempo_atual = time.time()
        vel_in_mbs = 0.0
        vel_out_mbs = 0.0
        
        if g_tempo_ant > 0:
            diff_tempo = tempo_atual - g_tempo_ant
            if diff_tempo > 0:
                vel_in_mbs = ((res["bytes_in"] - g_bytes_in_ant) / (1024**2)) / diff_tempo
                vel_out_mbs = ((res["bytes_out"] - g_bytes_out_ant) / (1024**2)) / diff_tempo
        
        vel_in_mbs = max(0.0, vel_in_mbs)
        vel_out_mbs = max(0.0, vel_out_mbs)

        g_bytes_in_ant = res["bytes_in"]
        g_bytes_out_ant = res["bytes_out"]
        g_tempo_ant = tempo_atual

        perc_grafico_in = min(1.0, (vel_in_mbs / REDE_MAX_VELOCIDADE_MBS))
        perc_grafico_out = min(1.0, (vel_out_mbs / REDE_MAX_VELOCIDADE_MBS))

        return {
            "IP": SSH_HOST,
            "HOSTNAME": res["hostname"],
            "USO_CPU": res["uso_cpu"] / 100,  # Flet usa progresso de 0.0 a 1.0
            "USO_MEMORIA": res["uso_memoria"] / 100,
            "TAMANHO_MEMORIA": res["tam_memoria"],
            "DISCO_ROOT_PERC": res["perc_disco"] / 100,
            "REDE_IN_MBS": round(vel_in_mbs, 2),
            "REDE_OUT_MBS": round(vel_out_mbs, 2),
            "PERC_GRAFICO_IN": perc_grafico_in,
            "PERC_GRAFICO_OUT": perc_grafico_out,
            "REDE_TOTAL_IN_MB": round(res["bytes_in"] / (1024**2), 1),
            "REDE_TOTAL_OUT_MB": round(res["bytes_out"] / (1024**2), 1)
        }
    except Exception as e:
        ULTIMO_ERRO = f"Falha de conexão: {e}"
        return None
    finally:
        ssh.close()

# ==============================================================================
# INTERFACE GRÁFICA INTERNA (FLET)
# ==============================================================================
def main(page: ft.Page):
    # 1. Configuração de Fontes Identidade Padrão (Carregadas diretamente da Web)
    page.fonts = {
        "RobotoMono": "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono%5Bwght%5D.ttf"
    }
    page.theme = ft.Theme(font_family="RobotoMono")
    
    page.title = "Dashboard de Telemetria Integrado"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 850
    page.window_height = 500
    page.window_resizable = False

    # --- Elementos Visuais: Hardware (Cores como strings diretas) ---
    pb_cpu = ft.ProgressBar(width=350, value=0, color="green")
    txt_cpu = ft.Text("Uso de CPU: 0%", size=14, weight=ft.FontWeight.BOLD)
    
    pb_mem = ft.ProgressBar(width=350, value=0, color="green")
    txt_mem = ft.Text("Uso de Memória RAM: 0%", size=14, weight=ft.FontWeight.BOLD)
    
    pb_disco = ft.ProgressBar(width=350, value=0, color="green")
    txt_disco = ft.Text("Armazenamento (Disco /): 0%", size=14, weight=ft.FontWeight.BOLD)

    # --- Elementos Visuais: Rede e Detalhes ---
    txt_host_info = ft.Text("Conectando ao servidor...", size=15, color="lightblue", weight=ft.FontWeight.BOLD)
    txt_mem_total = ft.Text("Memória Total Disponível: --", size=13, color="grey400")
    
    pb_net_in = ft.ProgressBar(width=350, value=0, color="greenaccent700")
    txt_net_in = ft.Text("⬇ Velocidade de Download: 0.0 MB/s", size=13, color="greenaccent400", weight=ft.FontWeight.BOLD)
    txt_total_in = ft.Text("Total acumulado recebido: -- MB", size=11, color="grey500")
    
    pb_net_out = ft.ProgressBar(width=350, value=0, color="orange700")
    txt_net_out = ft.Text("⬆ Velocidade de Upload: 0.0 MB/s", size=13, color="orange400", weight=ft.FontWeight.BOLD)
    txt_total_out = ft.Text("Total acumulado enviado: -- MB", size=11, color="grey500")

    # Status de Erro/Sincronização inferior
    txt_status = ft.Text(ULTIMO_ERRO, size=12, color="yellow700", italic=True)

    # --- Construção dos Painéis ---
    card_hardware = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("⚙️ Recursos do Sistema", size=18, weight=ft.FontWeight.BOLD, color="cyan"),
                ft.Divider(),
                ft.Column([txt_cpu, pb_cpu], spacing=5),
                ft.Column([txt_mem, pb_mem], spacing=5),
                ft.Column([txt_disco, pb_disco], spacing=5),
            ], spacing=20),
            padding=20
        ),
        expand=True
    )

    card_rede = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("🌐 Tráfego de Rede Real", size=18, weight=ft.FontWeight.BOLD, color="purple300"),
                ft.Divider(),
                txt_host_info,
                txt_mem_total,
                ft.Column([txt_net_in, pb_net_in, txt_total_in], spacing=2),
                ft.Column([txt_net_out, pb_net_out, txt_total_out], spacing=2),
            ], spacing=12),
            padding=20
        ),
        expand=True
    )

    # Adiciona a estrutura inicial na tela
    page.add(
        ft.Container(
            content=ft.Text("📊 DASHBOARD INTEGRADO DE TELEMETRIA", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            margin=ft.margin.only(bottom=15)
        ),
        ft.Row([card_hardware, card_rede], expand=True),
        ft.Row([txt_status], alignment=ft.MainAxisAlignment.CENTER)
    )

    def definir_cor_recurso(valor):
        if valor < 0.50: return "green"
        if valor < 0.80: return "yellow"
        return "red"

    # Loop de atualização assíncrona executada em Thread separada
    def dados_update_loop():
        while True:
            dados = coletar_dados_com_velocidade()
            
            if dados:
                # Atualizando Hardware
                pb_cpu.value = dados["USO_CPU"]
                pb_cpu.color = definir_cor_recurso(dados["USO_CPU"])
                txt_cpu.value = f"Uso de CPU: {int(dados['USO_CPU']*100)}%"
                
                pb_mem.value = dados["USO_MEMORIA"]
                pb_mem.color = definir_cor_recurso(dados["USO_MEMORIA"])
                txt_mem.value = f"Uso de Memória RAM: {int(dados['USO_MEMORIA']*100)}%"
                
                pb_disco.value = dados["DISCO_ROOT_PERC"]
                pb_disco.color = definir_cor_recurso(dados["DISCO_ROOT_PERC"])
                txt_disco.value = f"Armazenamento (Disco /): {int(dados['DISCO_ROOT_PERC']*100)}%"

                # Atualizando Rede e Host
                txt_host_info.value = f"Host: {dados['HOSTNAME']} | IP: {dados['IP']}"
                txt_mem_total.value = f"Memória Total Disponível: {dados['TAMANHO_MEMORIA']}"
                
                pb_net_in.value = dados["PERC_GRAFICO_IN"]
                txt_net_in.value = f"⬇ Velocidade de Download: {dados['REDE_IN_MBS']} MB/s"
                txt_total_in.value = f"Total acumulado recebido: {dados['REDE_TOTAL_IN_MB']} MB"
                
                pb_net_out.value = dados["PERC_GRAFICO_OUT"]
                txt_net_out.value = f"⬆ Velocidade de Upload: {dados['REDE_OUT_MBS']} MB/s"
                txt_total_out.value = f"Total acumulado enviado: {dados['REDE_TOTAL_OUT_MB']} MB"
                
                txt_status.value = "Conectado e sincronizado com sucesso."
                txt_status.color = "green"
            else:
                txt_status.value = f"⚠️ Erro: {ULTIMO_ERRO}"
                txt_status.color = "red"

            page.update()
            time.sleep(0.5)

    # Inicia a thread em background para não congelar o app gráfico
    thread = threading.Thread(target=dados_update_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    ft.app(target=main)