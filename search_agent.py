import ollama
import requests
import trafilatura
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

import sys_msgs

init(autoreset=True)
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
    print(f"{Fore.LIGHTRED_EX}GENERATING SEARCH QUERY...{Style.RESET_ALL}")
    search_query = query_generator()

    if search_query[0] == '"':
        search_query = search_query[1:-1]  # extract query if it is between ""

    print(f"{Fore.LIGHTRED_EX}Searching in DuckDuckGo...{Style.RESET_ALL}")
    search_results = duckduckgo_search(search_query)
    context_found = False
    while not context_found and len(search_results) > 0:  # Need to fix
        best_result = best_search_result(s_result=search_results, query=search_query)
        try:
            page_link = search_results[best_result]["link"]
        except:
            print(
                f"{Fore.LIGHTRED_EX}Failed to select best search result, trying again...{Style.RESET_ALL}"
            )
            continue
        page_text = scrape_webpage(page_link)
        print(
            f"{Fore.LIGHTGREEN_EX}Found {len(search_results)} results from the WEB{Style.RESET_ALL}"
        )
        search_results.pop(best_result)
        if page_text and contains_data_needed(
            search_content=page_text, query=search_query
        ):
            context = page_text
            context_found = True

    return context


def contains_data_needed(search_content, query):
    sys_msg = sys_msgs.contains_data_msg
    needed_prompt = f"PAGE_TEXT: {search_content} \nUSER_PROMPT: {assisstant_convo[-1]} \nSEARCH_QUERY: {query}"
    response = ollama.chat(
        model="llama3.1:latest",
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": needed_prompt},
        ],
    )
    content = response["message"]["content"]
    if "true" in content.lower():
        print(f"{Fore.LIGHTRED_EX}Here is the query: {query}{Style.RESET_ALL}")
        return True
    print(f"{Fore.LIGHTRED_EX}Founded data is not relevant{Style.RESET_ALL}")
    return False


def stream_assisstant_response():
    global assisstant_convo
    response_stream = ollama.chat(
        model="llama3.1:latest", messages=assisstant_convo, stream=True
    )
    complete_response = ""

    print("ASSISSTANT:")

    for chunc in response_stream:
        print(
            f"{Fore.LIGHTWHITE_EX}{chunc["message"]["content"]}{Style.RESET_ALL}",
            end="",
            flush=True,
        )
        complete_response += chunc["message"]["content"]
    assisstant_convo.append({"role": "assisstant", "content": complete_response})
    print("\n")


def main():
    global assisstant_convo
    while True:
        prompt = input(f"{Fore.LIGHTWHITE_EX}USER: \n")
        if prompt == "exit":
            break
        assisstant_convo.append({"role": "user", "content": prompt})
        if search_or_not():
            context = ai_search()
            # Remove last prompt after ai searched about it
            assisstant_convo = assisstant_convo[:-1]
            if context:
                prompt = f"SEARCH_RESULT: \n{context} \n\nUSER_PROMPT: {prompt}"
            else:
                prompt = (
                    f"USER PROMPT: \n{prompt} \n\nFAILED SEARCH: \nThe "
                    "AI search model was unable to extract any reliable data. Explain that "
                    "and ask if the user would like you to search again or respond "
                    "without web search context. Do not respond if a search was needed "
                    "and you are getting this message with anything but the above request "
                    "of how the user would like to proceed"
                )
            assisstant_convo.append({"role": "user", "content": prompt})
        stream_assisstant_response()
    print("PROGRAM IS CLOSED")


if __name__ == "__main__":
    main()
