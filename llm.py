import os
from typing import Dict, List, Optional, Tuple, Type, Any
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL")

GEMINI_API_PROD = os.getenv("GEMINI_API_PROD")
API_POOL_STRING = os.getenv("GEMINI_API_TEST", "")
GEMINI_API_POOL = [key.strip() for key in API_POOL_STRING.split(",") if key.strip()]

def create_llm(api_key: str, 
               model_name: str, 
               temperature: float = 0.7,
               thinking_level = None,
               structured_output: Optional[Type[BaseModel]] = None) -> ChatGoogleGenerativeAI:
    
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
    
    ) if not thinking_level else ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        thinking_level=thinking_level
    )

    if structured_output:
        llm = llm.with_structured_output(structured_output, method="json_mode")

    return llm

def llm_call(prompts: List[Tuple[str, str]],
             model:str = GEMINI_MODEL_NAME,
             prompt_variables: Optional[Dict[str, Any]] = None,
             temperature: float = 0.7,
             use_prod = False,
             use_test = True,
             thinking_level = None,
             structured_output: Optional[Type[BaseModel]] = None):
    
    prompts_template = ChatPromptTemplate.from_messages(prompts)
    inputs = prompt_variables if prompt_variables else {}

    if use_test and GEMINI_API_POOL:
        for i, api_key in enumerate(GEMINI_API_POOL):
            try:
                print(f"🔄 Tentativo di chiamata LLM con la chiave {i+1}/{len(GEMINI_API_POOL)}...")
                
                llm = create_llm(
                    api_key=api_key, 
                    model_name=model, 
                    temperature=temperature, 
                    thinking_level=thinking_level,
                    structured_output=structured_output
                )
                #print(f"SystemPrompt:\n{prompts_template.format_messages(**inputs)[0].content}")
                #print(f"UserPrompt:\n{prompts_template.format_messages(**inputs)[1].content}")
                chain = prompts_template | llm
                return chain.invoke(inputs)
                
            except Exception as e:
                print(f"⚠️ Chiave {i+1} fallita. Errore: {e}")
    if use_prod:
        llm = create_llm(
            api_key=GEMINI_API_PROD, 
            model_name=model, 
            temperature=temperature, 
            structured_output=structured_output
        )
        chain = prompts_template | llm
        return chain.invoke(inputs)