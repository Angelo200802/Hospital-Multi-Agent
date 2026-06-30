import os
from typing import Dict, List, Optional, Tuple, Type, Any
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception

load_dotenv()
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

def is_rate_limit_or_server_error(exception: Exception) -> bool:
    """
    Funzione di filtro per capire se l'errore è dovuto a limiti di quota (429) 
    o indisponibilità del server (503). In questi casi vogliamo fare il retry.
    Se l'errore è un errore di sintassi, API key invalida (400, 403), non facciamo retry.
    """
    err_msg = str(exception).lower()
    print(f"❌ Errore: {err_msg}")
    return "503" in err_msg or "unavailable" in err_msg


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

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(10),  
        retry=retry_if_exception(is_rate_limit_or_server_error),
        reraise=True, 
        before_sleep=lambda retry_state: print(f"⏳ Errore temporaneo. Applico backoff esponenziale: attendo prima del tentativo {retry_state.attempt_number + 1}...")
    )
    def _execute_chain_with_retry(llm_instance):
        chain = prompts_template | llm_instance
        return chain.invoke(inputs)

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

                return _execute_chain_with_retry(llm)
                
            except Exception as e:
                print(f"⚠️ Chiave {i+1} definitivamente fallita o limite superato dopo i tentativi. Errore finale: {e}")
    
    if use_prod:
        llm = create_llm(
            api_key=GEMINI_API_PROD, 
            model_name=model, 
            temperature=temperature, 
            structured_output=structured_output
        )
        chain = prompts_template | llm
        return chain.invoke(inputs)