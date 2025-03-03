# BasicLLMBackendServer
Simple, hostable flask app based server plus interface for any model you can fit


You will need to download the model weights on your own. I recommend choosing something lightweight like llama 3.2 1B instruct and using hugging face to download it.

### What is this really?
I made this as a personal research utility for quickly hosting a non-streaming LLM for inference purpsoes. It was a useful tool that helped me migrate from API calls to self-hosting.

There are substantial limitations to this tool, but it does a reasonable job at handling a queue of simple HTTP requests from multiple users. Mileage may vary.
