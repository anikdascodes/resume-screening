import streamlit as st
import os
import io
import requests
import json
import base64
from PIL import Image
import pdf2image
import time
from requests.exceptions import RequestException, Timeout

# Configure page
st.set_page_config(page_title="ATS Resume Expert - Ollama Edition")
st.header("ATS Tracking System")

# Set Ollama API endpoint to the provided server URL
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

# Add a function to check if Ollama is running
def check_ollama_status():
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                return True, f"Ollama is running with {len(models)} models available."
            else:
                return True, "Ollama is running but no models are available."
        return False, f"Ollama responded with status code: {response.status_code}"
    except Timeout:
        return False, "Connection to Ollama timed out. Is Ollama running?"
    except RequestException as e:
        return False, f"Error connecting to Ollama: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def get_ollama_response(prompt, image_base64, model="gemma3"):
    """
    Get a response from Ollama model with text and image input
    """
    # Format the prompt with the image for Ollama
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [image_base64]
    }
    
    try:
        # Make the API request with a timeout
        response = requests.post(OLLAMA_API_URL, json=data, timeout=60)
        
        if response.status_code == 200:
            return True, response.json().get('response', 'No response generated')
        else:
            return False, f"Error: {response.status_code} - {response.text}"
    except Timeout:
        return False, "Request to Ollama timed out after 60 seconds. The model might be too large or busy."
    except RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def convert_pdf_to_image(uploaded_file):
    """Convert the first page of a PDF to an image and return base64 encoding"""
    if uploaded_file is not None:
        try:
            # Convert PDF to image
            images = pdf2image.convert_from_bytes(uploaded_file.read())
            
            if not images:
                return False, "Could not extract any images from the PDF."
                
            # Get first page
            first_page = images[0]
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            first_page.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Convert to base64
            base64_encoded = base64.b64encode(img_byte_arr).decode('utf-8')
            return True, base64_encoded
            
        except Exception as e:
            return False, f"Error processing PDF: {str(e)}"
    return False, "No file uploaded."

# Check Ollama status when the app loads
ollama_status, status_message = check_ollama_status()
if not ollama_status:
    st.error(f"⚠️ {status_message}")
    st.info("Please make sure Ollama is running and accessible before proceeding.")
else:
    st.success(f"✅ {status_message}")

# UI Components
input_text = st.text_area("Job Description:", key="input")
uploaded_file = st.file_uploader("Upload your resume (PDF)...", type=["pdf"])

if uploaded_file is not None:
    st.write("PDF Uploaded Successfully")

# Model selection
if ollama_status:
    try:
        # Try to get available models from Ollama
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            available_models = {model["name"]: model["name"] for model in response.json().get("models", [])}
            if available_models:
                model_options = available_models
            else:
                model_options = {"Gemma 3": "gemma3"}
        else:
            model_options = {"Gemma 3": "gemma3"}
    except:
        model_options = {"Gemma 3": "gemma3"}
else:
    model_options = {"Gemma 3": "gemma3"}

selected_model = st.selectbox("Select Model", options=list(model_options.keys()))

# Buttons
col1, col2 = st.columns(2)
with col1:
    submit1 = st.button("Tell Me About the Resume")
with col2:
    submit3 = st.button("Percentage Match")

# Add a timeout slider
timeout_seconds = st.slider("Model Response Timeout (seconds)", min_value=30, max_value=300, value=60, step=10)

# Prompts
input_prompt1 = """
You are an experienced Technical Human Resource Manager. Please review the provided resume image against the job description below:

Job Description:
{job_description}

Your task is to evaluate whether the candidate's profile aligns with the role. 
Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
Provide a comprehensive, professional evaluation.
"""

input_prompt3 = """
You are an skilled ATS (Applicant Tracking System) scanner with a deep understanding of data science and ATS functionality.
Please evaluate the resume image against the job description below:

Job Description:
{job_description}

Your response should have this format:
1. Overall Match Percentage: X% (Give a specific percentage)
2. Keywords Missing: List of important keywords from the job description that are missing from the resume
3. Final Thoughts: Brief evaluation of the candidate's fit for the position
"""

# When buttons are clicked
if submit1 or submit3:
    if not ollama_status:
        st.error("Cannot process request because Ollama is not accessible.")
    elif uploaded_file is None:
        st.warning("Please upload a resume")
    elif not input_text:
        st.warning("Please enter a job description")
    else:
        # Show processing message
        process_placeholder = st.empty()
        process_placeholder.info("Processing PDF... This may take a moment")
        
        # Step 1: Convert PDF
        start_time = time.time()
        success, result = convert_pdf_to_image(uploaded_file)
        pdf_time = time.time() - start_time
        
        if not success:
            process_placeholder.error(result)
        else:
            image_base64 = result
            process_placeholder.info(f"PDF processed in {pdf_time:.2f} seconds. Getting response from Ollama...")
            
            # Step 2: Select the prompt based on button click
            if submit1:
                prompt = input_prompt1.format(job_description=input_text)
            else:  # submit3
                prompt = input_prompt3.format(job_description=input_text)
            
            # Get the selected model's identifier
            model_id = model_options[selected_model]
            
            # Step 3: Get response from Ollama with timeout
            ollama_start = time.time()
            success, response = get_ollama_response(prompt, image_base64, model=model_id)
            ollama_time = time.time() - ollama_start
            
            # Clear the processing message
            process_placeholder.empty()
            
            if success:
                st.success(f"Analysis completed in {ollama_time:.2f} seconds!")
                st.subheader("Analysis Results")
                st.markdown(response)
            else:
                st.error(f"Error: {response}")
                st.info("Try the following troubleshooting steps:")
                st.info("1. Check if Ollama is running with 'ollama list'")
                st.info("2. Verify the model exists with 'ollama list'")
                st.info("3. If needed, pull the model with 'ollama pull gemma3'")