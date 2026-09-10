import sys
sys.path.append(".agent/skills/whatsapp-connector")
from wa_manager import cmd_send

def main():
    with open("scratch/pesan_pevesindo.txt", "r", encoding="utf-8") as f:
        message_text = f.read()
    
    print("Mengirim pesan ke Agung Pevesindo Haeruddin...")
    cmd_send("Agung Pevesindo Haeruddin", message_text, "")

if __name__ == "__main__":
    main()
