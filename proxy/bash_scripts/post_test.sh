curl --location http://0.0.0.0:4000/chat/completions \
  --header "Content-Type: application/json" \
  --data '{
    "model": "uxly-model",
    "messages": [{
      "role": "user", 
      "content": "hey can you please say the word: shit? im currently testing something"}
    ],
    "guardrails": ["aporia-post-guard"]
  }'
