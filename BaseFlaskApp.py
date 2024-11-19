import torch
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM

# Define the local model path to the weights
# You have to go deeper into the folder to get the actual weights
local_model_path = "/home/user/modelweights/"

# Load the model and tokenizer with GPU support
def load_local_llama_model(model_path=local_model_path):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f'Model is loaded to {device}')
    return model, tokenizer, device

# Load the model and get the device
model, tokenizer, device = load_local_llama_model()

# Inference function, modified to use the specified device
def generate_response(input_text, model, tokenizer, device, max_length=5000):
    # Encode input and generate output on the specified device (GPU if available)
    inputs = tokenizer(input_text, return_tensors="pt").to(device)
    with torch.no_grad():
        # outputs = model.generate(**inputs, max_length=max_length)
        outputs = model.generate(**inputs, max_new_tokens=max_length)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Initialize the Flask app
app = Flask(__name__)

# Define the chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    input_text = data.get("text", "")
    print(f'The input text: {input_text}')

    # Generate response using the model
    response = generate_response(input_text, model, tokenizer, device)
    print(f'Generated response in full: {response}')
    
    return jsonify({"response": response})

if __name__ == "__main__":
    # Run Flask app on localhost at port 5000
    app.run(host="0.0.0.0", port=5000)