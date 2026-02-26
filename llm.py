import requests
import json
import re
from typing import List, Dict, Optional, Union
from openai import OpenAI


class LlamaCppClient:
    """Client for interacting with llama.cpp server using OpenAI Chat Completions API"""
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = "not-needed"):
        """
        Initialize the llama.cpp client
        
        Args:
            base_url: URL where llama.cpp server is running (default: http://localhost:8080)
            api_key: API key (not needed for local llama.cpp server, but required by OpenAI client)
        """
        self.base_url = base_url
        self.client = OpenAI(
            base_url=f"{base_url}/v1",
            api_key=api_key
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "Qwen3-4B-Instruct-2507-Q4_K_M",
        stream: bool = False,
        **kwargs
    ):
        """
        Send a chat completion request to llama.cpp server
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name (default: qwen-3-4b, but llama.cpp uses loaded model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters supported by llama.cpp
        
        Returns:
            Response from the model
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            print(f"Error during chat completion: {e}")
            raise
    
    def simple_query(self, query: str, system_prompt: Optional[str] = None) -> str:
        """
        Simple single-turn query to the model
        
        Args:
            query: User's question or prompt
            system_prompt: Optional system prompt to set context
        
        Returns:
            Model's response as string
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": query})
        
        return self.chat_completion(messages)
    
    def multi_turn_chat(
        self,
        conversation_history: List[Dict[str, str]],
        new_message: str
    ) -> str:
        """
        Continue a multi-turn conversation
        
        Args:
            conversation_history: Previous messages in the conversation
            new_message: New user message to add
        
        Returns:
            Model's response
        """
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": new_message})
        
        response = self.chat_completion(messages)
        return response
    
    def check_server_status(self) -> bool:
        """
        Check if llama.cpp server is running and responding
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def query_with_json_response(
        self,
        query: str,
        system_prompt: str,
        max_retries: int = 2,
        **kwargs
    ) -> Dict:
        """
        Query the model and parse JSON response with retry logic
        
        Args:
            query: User's question or prompt
            system_prompt: System prompt to set context
            max_retries: Number of retries if JSON parsing fails
            **kwargs: Additional parameters for chat completion
        
        Returns:
            Parsed JSON response as dictionary
        """
        for attempt in range(max_retries + 1):
            try:
                response_text = self.simple_query(query, system_prompt)
                
                # Clean up response to extract JSON
                json_data = self._extract_json_from_response(response_text)
                
                return json_data
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    # Add instruction to fix JSON format
                    query += "\n\nIMPORTANT: Respond ONLY with valid JSON, no markdown or extra text."
                    continue
                else:
                    # Return error structure
                    return {
                        "error": "JSON parsing failed",
                        "raw_response": response_text,
                        "parse_error": str(e)
                    }
            except Exception as e:
                return {
                    "error": "Query failed",
                    "exception": str(e)
                }
        
        return {"error": "Max retries exceeded"}
    
    def _extract_json_from_response(self, text: str) -> Dict:
        """
        Extract and parse JSON from LLM response, handling markdown code blocks
        
        Args:
            text: Raw response text from LLM
        
        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks if present
        text = text.strip()
        
        # Pattern 1: ```json ... ```
        if text.startswith("```json"):
            text = text[7:]
        # Pattern 2: ``` ... ```
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        # Try to find JSON object or array
        # Look for first { or [ and last } or ]
        json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        return json.loads(text)
    
    def analyze_privacy(
        self,
        text: str,
        filename: str = "",
        context: str = ""
    ) -> Dict:
        """
        Analyze text for personal or sensitive information using privacy-focused prompt
        
        Args:
            text: Text to analyze for privacy concerns
            filename: Optional filename for context
            context: Optional additional context about the source
        
        Returns:
            Dictionary with structured privacy analysis
        """
        system_prompt = """You are an expert privacy and security analyst specializing in detecting sensitive information.

Your task is to analyze text and identify any personal, confidential, or sensitive information that could pose privacy or security risks.

CATEGORIES TO DETECT:

1. Personal Identifiers:
   - Full names, addresses, phone numbers, email addresses
   - Date of birth, age, gender, nationality
   - Physical descriptions, photos with identifiable features

2. Government/Official IDs:
   - Social Security Numbers (SSN), Tax IDs
   - Passport numbers, Visa information
   - Driver's license numbers
   - Student ID numbers, Employee IDs
   - National ID numbers

3. Financial Information:
   - Credit/debit card numbers
   - Bank account numbers, IBAN, SWIFT codes
   - Payment transaction details
   - Salary, income information
   - Financial statements

4. Authentication Credentials:
   - Usernames and passwords
   - API keys, tokens, access codes
   - Security questions/answers
   - Two-factor authentication codes
   - PIN codes

5. Medical/Health Information:
   - Medical records, diagnoses
   - Prescription information
   - Health insurance details
   - Medical test results
   - Mental health information

6. Biometric Data:
   - Fingerprints, facial recognition data
   - Retinal scans, DNA information
   - Voice recordings (identification)

7. Confidential/Proprietary:
   - Trade secrets, business plans
   - Confidential communications
   - Internal company documents
   - Proprietary algorithms or code
   - Non-public business information

RISK LEVELS:
- critical: Immediate security threat (passwords, SSN, credit cards)
- high: Serious privacy concern (passport, medical records, financial data)
- medium: Moderate risk (full name + address, employee ID)
- low: Minor concern (just first name, generic email)
- none: No sensitive information detected

RESPONSE FORMAT (JSON only, no markdown):
{
    "contains_sensitive_info": true or false,
    "risk_level": "none/low/medium/high/critical",
    "detected_categories": ["category1", "category2"],
    "specific_findings": ["finding1", "finding2"],
    "recommendations": ["action1", "action2"],
    "confidence": "high/medium/low"
}

Be thorough but precise. Only flag actual sensitive information, not generic content."""

        context_parts = []
        if filename:
            context_parts.append(f"Filename: {filename}")
        if context:
            context_parts.append(f"Context: {context}")
        
        context_str = "\n".join(context_parts) if context_parts else "Source: Image OCR extraction"
        
        user_prompt = f"""{context_str}

TEXT TO ANALYZE:
{text}

Analyze the above text for sensitive information and respond with ONLY valid JSON in the specified format."""

        result = self.query_with_json_response(
            query=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1500
        )
        
        # Add metadata
        if "error" not in result:
            result["filename"] = filename
            result["analyzed_text_length"] = len(text)
        
        return result
    
    def batch_analyze_privacy(
        self,
        texts: List[Dict[str, str]],
        progress_callback=None
    ) -> List[Dict]:
        """
        Analyze multiple texts for privacy concerns
        
        Args:
            texts: List of dicts with 'text', 'filename', 'context' keys
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            List of analysis results
        """
        results = []
        total = len(texts)
        
        for idx, item in enumerate(texts, 1):
            if progress_callback:
                progress_callback(idx, total, f"Analyzing {item.get('filename', f'item {idx}')}")
            
            result = self.analyze_privacy(
                text=item.get('text', ''),
                filename=item.get('filename', ''),
                context=item.get('context', '')
            )
            
            results.append(result)
        
        return results
    
    def summarize_privacy_results(self, results: List[Dict]) -> Dict:
        """
        Generate summary statistics from privacy analysis results
        
        Args:
            results: List of privacy analysis results
        
        Returns:
            Summary dictionary with counts and statistics
        """
        summary = {
            "total_analyzed": len(results),
            "contains_sensitive": sum(1 for r in results if r.get("contains_sensitive_info", False)),
            "risk_levels": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "none": 0,
                "error": 0
            },
            "all_categories": set(),
            "high_risk_files": []
        }
        
        for result in results:
            risk = result.get("risk_level", "error")
            if risk in summary["risk_levels"]:
                summary["risk_levels"][risk] += 1
            
            # Collect all detected categories
            categories = result.get("detected_categories", [])
            summary["all_categories"].update(categories)
            
            # Track high-risk files
            if risk in ["critical", "high"]:
                summary["high_risk_files"].append({
                    "filename": result.get("filename", "Unknown"),
                    "risk_level": risk,
                    "categories": categories
                })
        
        summary["all_categories"] = list(summary["all_categories"])
        
        return summary


# Example usage and helper functions
def start_conversation(client: LlamaCppClient, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Start a new conversation with optional system prompt
    
    Args:
        client: LlamaCppClient instance
        system_prompt: Optional system prompt
    
    Returns:
        Initialized conversation history
    """
    conversation = []
    if system_prompt:
        conversation.append({"role": "system", "content": system_prompt})
    return conversation


def main():
    """Example usage of LlamaCppClient with privacy analysis"""
    
    # Initialize client
    print("Initializing llama.cpp client...")
    client = LlamaCppClient(base_url="http://localhost:8080")
    
    # Check server status
    if not client.check_server_status():
        print("Warning: llama.cpp server is not responding. Make sure it's running.")
        print("\nTo start llama.cpp server with Qwen 3 4B:")
        print("./llama-server -m path/to/qwen-3-4b.gguf --port 8080")
        return
    
    print("Server is running!\n")
    
    # Example 1: Simple query
    print("=== Example 1: Simple Query ===")
    response = client.simple_query(
        query="What is the capital of France?",
        system_prompt="You are a helpful assistant."
    )
    print(f"Response: {response}\n")
    
    # Example 2: Privacy Analysis (Main Use Case)
    print("=== Example 2: Privacy Analysis ===")
    sample_text = """
    John Smith
    123 Main Street, New York, NY 10001
    Phone: (555) 123-4567
    Email: john.smith@email.com
    SSN: 123-45-6789
    """
    
    result = client.analyze_privacy(
        text=sample_text,
        filename="sample_id.jpg",
        context="Scanned document"
    )
    
    print(f"Analysis Result:")
    print(f"  Contains Sensitive Info: {result.get('contains_sensitive_info')}")
    print(f"  Risk Level: {result.get('risk_level')}")
    print(f"  Categories: {', '.join(result.get('detected_categories', []))}")
    print(f"  Findings: {result.get('specific_findings')}")
    print(f"  Recommendations: {result.get('recommendations')}\n")
    
    # Example 3: Batch Analysis
    print("=== Example 3: Batch Privacy Analysis ===")
    texts_to_analyze = [
        {
            "text": "Meeting scheduled for 3 PM tomorrow.",
            "filename": "memo.jpg"
        },
        {
            "text": "Credit Card: 4532-1234-5678-9010, Exp: 12/25",
            "filename": "receipt.jpg"
        },
        {
            "text": "Hello, my name is Alice.",
            "filename": "note.jpg"
        }
    ]
    
    batch_results = client.batch_analyze_privacy(
        texts_to_analyze,
        progress_callback=lambda c, t, m: print(f"  [{c}/{t}] {m}")
    )
    
    # Show summary
    summary = client.summarize_privacy_results(batch_results)
    print(f"\nBatch Analysis Summary:")
    print(f"  Total Analyzed: {summary['total_analyzed']}")
    print(f"  Contains Sensitive: {summary['contains_sensitive']}")
    print(f"  Risk Levels: {summary['risk_levels']}")
    print(f"  All Categories Found: {summary['all_categories']}")
    
    if summary['high_risk_files']:
        print(f"\n  ⚠️ High Risk Files:")
        for file in summary['high_risk_files']:
            print(f"    - {file['filename']} ({file['risk_level']}): {file['categories']}")
    
    # Example 4: Streaming response (optional)
    print("\n=== Example 4: Streaming Response ===")
    print("User: Write a haiku about AI")
    print("Assistant: ", end="", flush=True)
    
    stream = client.chat_completion(
        messages=[{"role": "user", "content": "Write a haiku about AI"}],
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    main()
