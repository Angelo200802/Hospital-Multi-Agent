import os
from typing import Dict, List, Optional, Tuple, Type, Any
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL")
GEMINI_API_KEY_TEST = os.getenv("GEMINI_API_TEST")
GEMINI_API_KEY = os.getenv("GEMINI_API")

def create_llm(api_key: str, 
               model_name: str, 
               temperature: float = 0.7,
               structured_output: Optional[Type[BaseModel]] = None,  
               tools: Optional[List] = None) -> ChatGoogleGenerativeAI:
    
    actual_tools = None if structured_output else tools

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        tools=actual_tools
    )

    if structured_output:
        llm = llm.with_structured_output(structured_output, method="json_mode")

    return llm

def llm_call(prompts: List[Tuple[str, str]],
             prompt_variables: Optional[Dict[str, Any]] = None, 
             temperature: float = 0.7,
             structured_output: Optional[Type[BaseModel]] = None,
             tool: Optional[List] = None):
    
    prima_chiave = GEMINI_API_KEY_TEST if GEMINI_API_KEY_TEST else GEMINI_API_KEY
    
    llm = create_llm(
        api_key=prima_chiave, 
        model_name=GEMINI_MODEL_NAME, 
        temperature=temperature, 
        structured_output=structured_output, 
        tools=tool
    )

    prompts_template = ChatPromptTemplate.from_messages(prompts)
    chain = prompts_template | llm

    inputs = prompt_variables if prompt_variables else {}

    try:
        return chain.invoke(inputs)
    except Exception as e:
        print(f"⚠️ Errore con la prima chiave LLM: {e}")
        
        # SCATTA IL FALLBACK: Proviamo la chiave di produzione SOLO se è DIVERSA da quella appena fallita
        if GEMINI_API_KEY_TEST and GEMINI_API_KEY and GEMINI_API_KEY_TEST != GEMINI_API_KEY:
            print("🔄 Tentativo di fallback sulla chiave di produzione...")
            try:
                llm_fallback = create_llm(
                    api_key=GEMINI_API_KEY, 
                    model_name=GEMINI_MODEL_NAME, 
                    temperature=temperature, 
                    structured_output=structured_output, 
                    tools=tool
                )
                chain_fallback = prompts_template | llm_fallback
                return chain_fallback.invoke(inputs)
            except Exception as fallback_error:
                print(f"❌ Fallito anche il fallback in produzione: {fallback_error}")
                raise fallback_error
        else:
            raise e