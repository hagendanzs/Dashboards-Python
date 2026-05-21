from pylogix import PLC

# Cria a conexão definindo o IP do controlador
with PLC() as comm:
    comm.IPAddress = '172.16.35.30'
    # Define o slot do processador (padrão é 0 se omitido)
    comm.ProcessorSlot = 2 
    
    # Executa a leitura da tag chamada 'Minha_Tag_Inteira'
    resultado0 = comm.Read('Timer[0].acc')
	
    # Executa a leitura da tag chamada 'Minha_Tag_Inteira'
    resultado1 = comm.Read('Conta[0].acc')
	
    # Executa a leitura da tag chamada 'Minha_Tag_Inteira'
    resultado2 = comm.Read('Conta[1].acc')
	
    # Exibe o valor retornado
    print(resultado0.TagName, resultado0.Value, resultado0.Status)
	
    # Exibe o valor retornado
    print(resultado1.TagName, resultado1.Value, resultado1.Status)
	
	# Exibe o valor retornado
    print(resultado2.TagName, resultado2.Value, resultado2.Status)