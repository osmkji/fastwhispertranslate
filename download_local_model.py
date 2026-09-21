from faster_whisper import download_model

# Download the "large-v3" model to a local directory called "models/large-v3"
model_path = download_model("large-v3", output_dir="models/large-v3")
print(f"Model successfully downloaded to: {model_path}")
