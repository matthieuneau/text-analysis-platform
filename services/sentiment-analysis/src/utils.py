"""
Simple script to download and convert Hugging Face model to ONNX format
"""

from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer


def convert_to_onnx():
    """Download and convert the sentiment model to ONNX format"""

    model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    output_dir = "./models"

    print(f"Converting {model_name} to ONNX...")

    # Download and convert model to ONNX in one step
    model = ORTModelForSequenceClassification.from_pretrained(model_name, export=True)

    # Download tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Save both model and tokenizer
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"✅ Model converted and saved to {output_dir}")
    print("📁 Files created:")
    print("   - model.onnx")
    print("   - tokenizer files")


if __name__ == "__main__":
    convert_to_onnx()
