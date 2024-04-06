import openai
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from rich.markdown import Markdown
from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding
from rich.prompt import Prompt
from tinydb import TinyDB
import os

db = TinyDB('db.json')
console = Console()

load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")
client = openai.OpenAI(api_key=API_KEY)
# messages = [{"role": "system", "content": "You are an assistant who understands a lot about history, technology and programming languages."}]

# armazenamento e recuperação de threads
def store_thread(thread: Dict, index: int, db: TinyDB, console: Console) -> bool:
    updated = db.update(thread, doc_ids=[index])
    if updated[0]:
        console.print(f"A thread nº {updated[0]} foi atualizada!")
        return True
    else:
        return False

def recovery_thread(index) -> Dict: # {"topic": str, "messages": List}
    result = db.get(doc_id=index)
    return result if result else {}

def recovery_threads() -> List[tuple]: # retorna tuplas (number, topic)
    result: List[tuple] = [(i.doc_id, i["topic"]) for i in db.all()]
    return result

def create_thread(console: Console) -> Tuple:
    assistant_role = console.input("Escreva como deve ser o assistente (com todos os detalhes de como deve responder): >> ")
    topic = console.input("Escreva o tema/assunto desta Thread >> ")
    match int(console.input("Escolha o modelo [1 -> gpt4(32k), 2 -> gpt4(128k), 3 -> gpt3.5(16k)]")):
        case 1:
            model = "gpt-4-32k-0613"
        case 2:
            model = "gpt-4-1106-preview"
        case 3:
            model = "gpt-3.5-turbo-1106"
        case _:
            console.print("Modelo inválido. Lançando erro!")
            raise ValueError
    thread = {
        "topic": topic,
        "messages": [{"role": "system", "content": assistant_role}],
        "model": model
    }
    doc_id = db.insert(thread)
    return thread, doc_id

# interação com a API da OpenAI
def make_request(question_input: str, messages: List, model: str):
    messages.append({"role": "user", "content": f"{question_input}"})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.8,
    )
    messages.append({"role": response.choices[0].message.role, "content": response.choices[0].message.content})

# entrypoint
def main(console, db):
    # Criação da UI inicial para a esclha das threads
    console.clear()
    index_threads: List[tuple] = recovery_threads() # retorna tuplas (número, assunto) para haver a escolha da conversa
    for i in index_threads:
        console.print(f"Diálogo {i[0]} - Tópico: {i[1]}\n")
    try:
        choice = int(console.input("Escolha o número do tópico: [se novo, digite -1] >>"))
    except:
        console.print("Escolha inválida")
        exit(1)
    if choice == -1:
        data_thread, index = create_thread(console)
    else:
        
        data_thread: Dict = recovery_thread(choice)
        index = choice
        if not data_thread:
            console.print("Escolha inválida")
            exit(1)

    while True:
        # Criação da UI de diálogo
        console.clear()
        console.print(f"[bold green]Tópico: { data_thread['topic'] }[/bold green]\n\n")
        model = data_thread.get("model") or "gpt-3.5-turbo-1106"
        messages: List = data_thread["messages"]
        for l in messages:
            if l["role"] == "system":
                console.print((f":robot:  Descrição do assistente: [italic] {l['content']} [/italic]"), style="dark_slate_gray1 bold")
            elif l["role"] == "assistant":
                role_md = Markdown(f"{l['content']}\n")
                console.print(Padding(':robot_face: [green bold]Assistente:[/green bold] ', (1,2)), role_md)
            elif l["role"] == "user":
                user_md = Markdown(f"{l['content']}\n")
                user_pm = Panel(user_md)
                console.print(Padding("[bold purple]:smile: User:>>[/bold purple]", (1,2)), user_pm)
        text = console.input(Padding("[bold blue]:smiley: Prompt:>>[/bold blue]", (1,2)))
        # Diáogo com usuário
        if text == "":
            continue
        elif text== "\q":
            break
        console.print("\n:thought_balloon: Pensando... Aguarde.")
        make_request(text, messages=messages, model=model)
       
    if store_thread(data_thread, index=index, db=db, console=console):
        exit(0)
    else:
        console.print("Dados da conversa não foram salvos. Arquivo produzido com os dados em txt.")
        with open("backup_conversa.txt", "x") as file:
            for l in data_thread:
                file.write(str(l))
        exit(1)

if __name__ == "__main__":
    main(console, db)