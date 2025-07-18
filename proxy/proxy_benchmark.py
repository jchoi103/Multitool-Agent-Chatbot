import requests
import os

url = "http://0.0.0.0:4000"
headers = {"Content-Type": "application/json"}

def load_prompts(folder_path):
    dict_return = {} 
    for file in os.listdir(folder_path):
        file_path = folder_path + "/" + file
        #print(file_path, file)
        with open(file_path, "r") as text:
            dict_return[file] = [line.strip() for line in text if line.strip()]
    return dict_return


parsed_data = load_prompts("question_queries")
#print(parsed_data)
#test_prompts_1 = load_prompts("question_queries/query_list_1.txt")
# test_prompts_2 = load_prompts("question_queries/query_list_2.txt")
# test_prompts_3 = load_prompts("question_queries/query_list_3.txt")
# test_prompts_4 = load_prompts("question_queries/query_list_4.txt")

def proxy_test(data_dict):
    for file, prompts in data_dict.items():
        response_file = "response_" + file
        response_path = "response_queries/" + response_file

        print(f"\n[PROCESSING BENCHMARK FILE - {file}]")
        for i in range(len(prompts)):
            prompt = prompts[i]
            print(f"\nTEST ({i}) - Question: {prompt}")
            
            payload = {
                "model": "uxly-model",
                "messages": [{"role": "user", "content": f"<question>{prompt}</question>"}],
                "guardrails": [
                    "aporia-pre-guard",
                    "aporia-post-guard"
                ]
            }
            try:
                response = requests.post(url, json=payload, headers=headers)
                response_data = response.json()
                
                if 'error' in response_data:
                    error = response_data['error']
                    message = error.get('message', {}).get('error', 'Unknown error') 
                    aporia_ai_response = error.get('message', {}).get('aporia_ai_response', {})
                    bot_response = aporia_ai_response.get('revised_response', 'No revision')
                    
                    print(f"Error Detected: {message}")
                else:
                    bot_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                    
                print(f"Aporia's Response: {bot_response}\n")
                
                # Append responses instead of overwriting
                with open(response_path, "a") as new_file:
                    new_file.write(f"Question: {prompt}\nResponse: {bot_response}\n\n")
            
            except Exception as e:
                print(f"File = {file} | Question = {prompt} -> Error: {e}\n")
            
        print("Responses saved to: " + response_path)

proxy_test(parsed_data)