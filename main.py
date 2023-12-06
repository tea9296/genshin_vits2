from pynput import keyboard,mouse
import pyautogui
import json
import os,glob,time
from pathlib import Path
import easyocr
from zhconv import convert
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "vits2"))
os.chdir(os.path.join(os.getcwd(), 'vits2'))

import vits2.inf as inf
config_path = "../config.json"



def get_character_sim(model_config_path:str)->dict:
    """get the character similarity from the model config file

    Args:
        model_config_path (str): path to the model config file

    Returns:
        dict: character similarity
    """
    spk_list = Path(model_config_path + "spks.json").read_text(encoding="utf-8")
    speakers = json.loads(spk_list)
    ret = {}
    
    for speaker in speakers:
        ret[convert(speaker,'zh-hant')] = speaker
    
    return ret



def load_config():
    """setting the global variables from the config file
    """
    global config_path, PATH, MAIN_CHARACTER, KEY_PRESS, CHA_SIM_DICT, reader, model
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    PATH = config["tmp_path"]
    MAIN_CHARACTER = convert(config["main_character"], 'zh-cn')
    KEY_PRESS = config["key_press"]
    LANGUAGE = config["language"]     
    CHA_SIM_DICT = get_character_sim(config["model_config_path"])
    Path(PATH).mkdir(parents=True, exist_ok=True)
    reader = easyocr.Reader([LANGUAGE,'en'], gpu=True)
    model = inf.vits2(default_spearker = convert(config["default_character"], 'zh-cn'), model_config_path = config["model_config_path"], tmp_path = PATH)

    
load_config()




def on_press(key):
    """on press function for the listener

    Args:
        key (): key press

    Returns:
        _type_: _description_
    """
    if key == keyboard.Key[KEY_PRESS]:
        print(f'{KEY_PRESS} pressed')
        filename, width, height = take_screenshot()
        try:
            main_text, npc_text, npc_name = ocr(filename, width, height)
            if npc_name in CHA_SIM_DICT:
                npc_name = CHA_SIM_DICT[npc_name]
                
            
            ### generate npc wav file and play it ###
            if npc_text != "":
                status, npc_wav_path = model.generate(npc_text, npc_name)
                if status == "成功":
                    model.play_wav(npc_wav_path)
                else:
                    print(f"generate {npc_name} failed\n")
            
            
            ### generate main character wav file and play it ###
            if main_text != "":
                status, main_wav_path = model.generate(main_text, MAIN_CHARACTER)
                if status == "成功":
                    model.play_wav(main_wav_path)
                else:
                    print(f"generate {MAIN_CHARACTER} failed\n")
        except Exception as e:
            print(e, "\n")
            
        delete_old_temp_files(PATH)  ## delete old files in the tmp folder
    if key == keyboard.Key.scroll_lock:
        # Stop listener
        return False




def take_screenshot()->(str,int,int):
    """take a screenshot of the lower half of the screen and start at the 200 of the x axis, 
    save it in the tmp folder and return the file path, width and height

    Returns:
        (str,int,int): file_path, width, height
    """

    
    
    ## get a file name based on the number of png files in the folder
    # Get a list of all PNG files in the directory
    png_files = glob.glob(os.path.join(PATH, '*.png'))

    # Count the number of PNG files
    num_png_files = len(png_files)

    # Create a new file name based on the count
    new_file_name = f'{num_png_files + 1}.png'
    
    new_file_path = os.path.join(PATH, new_file_name)
    
    # Get the size of the screen
    screen_width, screen_height = pyautogui.size()

    # Calculate the region of the lower half of the screen
    
    region = (0, screen_height // 2, screen_width, screen_height )
    # Take a screenshot of the lower half of the screen
    screenshot = pyautogui.screenshot(region=region)
    width, height = screenshot.size
    # Save the screenshot
    screenshot.save(new_file_path)
    
    return new_file_path, width, height//2







def ocr(filepath:str, width:int, height:int):

    result = reader.readtext(filepath,width_ths=1.0)
    count = 0
    main_text, npc_text, npc_name = "", "", ""
    for res in result:
        if res[0][0][0] < width//2:
            print("talking person: ", res[1])
            npc_name = res[1]
            count += 1
            break
        
        ## main character text
        main_text += process_text(res[1]) 
        print(res[1])   
        count += 1
    
    ## skip description of character
    if count < len(result) and result[count][0][0][0] > width//2:
        #print("person title: ", result[count][1])
        count += 1
    
    ## get talking person text
    for i in range(count,len(result)):

        ## ignore uid
        if result[i][0][0][1] >= int(height*0.85) or ("1D:" in result[i][1]) or ("ID" in result[i][1]):
            #print("UID: ", result[i][1])
            continue
        print(result[i][1])
        npc_text += process_text(result[i][1]) 
        
   
    return main_text, npc_text, npc_name.replace(' ', '')


def process_text(text:str):

    text = text.replace(" ", "")
    
    if len(text) > 0 and (text[-1] == "o" or text[-1]=="0" or text[-1]=="O"):
        return text[:-1] + "。"
    
    return text
    
def delete_old_temp_files(path:str):
    """delete all files in the tmp folder that create more than 10 mins ago
    """
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.stat(file_path).st_mtime < time.time() - 600:
            if os.path.isfile(file_path):
                os.remove(file_path)
                #print("delete file: ", file_path)







# Start the listener
with keyboard.Listener(on_press=on_press) as listener:
    print(f"\n\npress \'{KEY_PRESS}\' to start, press \'scroll lock\' to exit.\n\n")
    print("start listening....\n\n")
    listener.join()
