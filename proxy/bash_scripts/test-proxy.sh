curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "uxly-model",
      "messages": [
        {
          "role": "user",
          "content": "say hello in mandarin chinese"
        }
      ]
    }
'
