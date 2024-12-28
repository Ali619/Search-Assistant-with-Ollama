import ollama

assisstant_convo = []


def stream_assisstant_response():
    global assisstant_convo
    response_stream = ollama.chat(
        model="llama3.1:latest", messages=assisstant_convo, stream=True
    )
    complete_response = ""

    print("ASSISSTANT:")

    for chunc in response_stream:
        print(chunc["message"]["content"], end="", flush=True)
        complete_response += chunc["message"]["content"]
    assisstant_convo.append({"role": "assisstant", "content": complete_response})
    print("\n")


def main():
    global assisstant_convo
    while True:
        prompt = input("USER: \n")
        if prompt == "exit":
            break
        assisstant_convo.append({"role": "user", "content": prompt})
        stream_assisstant_response()
    print("PROGRAM IS CLOSED")


if __name__ == "__main__":
    main()
