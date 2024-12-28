import ollama
import requests
import trafilatura
from bs4 import BeautifulSoup

import sys_msgs

assisstant_convo = [sys_msgs.assistant_msg]


def search_or_not():
    sys_msg = sys_msgs.search_or_not_msg
    response = ollama.chat(
        model="llama3.1:latest",
        messages=[{"role": "system", "content": sys_msg}, assisstant_convo[-1]],
    )
    content = response["message"]["content"]
    if "true" in content.lower():
        return True
    return False


def query_generator():
    sys_msg = sys_msgs.query_msg
    query_msg = f"CREATE A SEARCH QUERY FOR THIS PROMPT: \n{assisstant_convo[-1]}"
    response = ollama.chat(
        model="llama3.1:latest",
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": query_msg},
        ],
    )
    return response["message"]["content"]


def duckduckgo_search(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.1; Win64;) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.30.29.110 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={query}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for i, result in enumerate(soup.find_all("div", class_="result"), start=1):
        if i > 10:
            break
        title_tag = result.find("a", class_="result__a")
        if not title_tag:
            continue

    link = title_tag["href"]
    snippet_tag = result.find("a", class_="result_snipper")
    snippet = snippet_tag.text_strip() if snippet_tag else "No description available"
    results.append({"id": i, "link": link, "search_description": snippet})
    return results


def best_search_result(s_result, query):
    sys_msg = sys_msgs.best_search_msg
    best_msg = f"SEARCH_RESULTS: {s_result} \nUSER_PROMPT: {assisstant_convo[-1]} \nSEARCH_QUERY: {query}"

    for _ in range(2):
        # Give 2 chance to model to score the search results (Fine-tuning or few-shot could be a better way)
        try:
            response = ollama.chat(
                model="llama3.1:latest",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": best_msg},
                ],
            )
            return int(response["message"]["content"])
        except:
            continue
    return 0


def scrape_webpage(url):
    try:
        downloaded = trafilatura.fetch_url(url=url)
        return trafilatura.extract(
            downloaded, include_formatting=True, include_links=True
        )
    except:
        return None


def ai_search():
    context = None
    print("GENERATING SEARCH QUERY")
    search_query = query_generator()

    if search_query[0] == '"':
        search_query = search_query[1:-1]  # extract query if it is between ""

    search_results = duckduckgo_search(search_query)
    context_found = False
    while not context_found and len(search_results) > 0:
        best_result = best_search_result(s_result=search_results, query=search_query)
        try:
            page_link = search_results[best_result]["link"]
        except:
            print("Failed to select best search result, trying again...")
            continue
        page_text = scrape_webpage(page_link)
        search_results.pop(best_result)


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
        if search_or_not():
            context = ai_search()
        stream_assisstant_response()
    print("PROGRAM IS CLOSED")


if __name__ == "__main__":
    main()
