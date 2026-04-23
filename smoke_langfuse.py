from dotenv import load_dotenv
load_dotenv()

from langfuse import observe

@observe()
def test():
    return "hello from langfuse"

if __name__ == "__main__":
    print(test())