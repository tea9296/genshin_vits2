import sys, os, re, json
from glob import glob
from tqdm import tqdm
import numpy as np
import soundfile as sf
import requests as req

if sys.platform == "darwin":
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"


import torch
import commons as commons
import utils as utils
import hashlib
import random
from pathlib import Path
from models import SynthesizerTrn
from text.symbols import symbols
from text import cleaned_text_to_sequence, get_bert
from text.cleaner import clean_text
import jieba
import logging
jieba.setLogLevel(logging.INFO)


def get_text(text, language_str, hps):
    norm_text, phone, tone, word2ph = clean_text(text, language_str)
    phone, tone, language = cleaned_text_to_sequence(phone, tone, language_str)

    if hps.data.add_blank:
        phone = commons.intersperse(phone, 0)
        tone = commons.intersperse(tone, 0)
        language = commons.intersperse(language, 0)
        for i in range(len(word2ph)):
            word2ph[i] = word2ph[i] * 2
        word2ph[0] += 1
    bert = get_bert(norm_text, word2ph, language_str)
    del word2ph

    assert bert.shape[-1] == len(phone)

    phone = torch.LongTensor(phone)
    tone = torch.LongTensor(tone)
    language = torch.LongTensor(language)

    return bert, phone, tone, language

def get_spk(spklist):
    data = json.loads(spklist)
    return data



def search_speaker(search_value, speakers):
    for s in speakers:
        if search_value == s:
            return s
    for s in speakers:
        if search_value in s:
            return s

def split_text(input_string):
   pattern = r'[,.;?!，。？！|]'
   parts = re.split(f'({pattern})', input_string)
   parts = ["".join(group) for group in zip(parts[::2], parts[1::2])]
   parts = [part for part in parts if part != '']
   return [part.replace("|","") for part in parts]

def replace_string(input_string: str) -> str:
    input_string = input_string.replace(" ", "")
    input_string = input_string.replace("|\n", "\n").replace("|", "\n")
    input_string = input_string.replace(":", "：")
    sentences = input_string.split("\n")
    sentences = [x for x in sentences if x]
    result = []
    for sent in sentences:
    
        if "：" in sent:
            seg = sent.split("：")
            spk = seg[0]
            content =  seg[1]
            sents = spk + "：" + content
            result.append(sents)
        else:
            sents = sent
            result.append(sents)
    output_string = "|".join(result)
    return output_string


def add_period(text):
    if not re.search(r'[^\w\s]', text[-1]):
        text += '。'
    return text



class vits2:
    def __init__(self, default_spearker = "卡芙卡", model_config_path = "./vits2/models/genshin/", tmp_path = "./temp"):
        
        ### set default params ###
        model = model_config_path + "model.pth"
        config = model_config_path + "config.json"
        spk_list = Path(model_config_path + "spks.json").read_text(encoding="utf-8")
        self.hps = utils.get_hparams_from_file(config)
        self.device = (
                "cuda:0"
                if torch.cuda.is_available()
                else (
                    "mps"
                    if sys.platform == "darwin" and torch.backends.mps.is_available()
                    else "cpu"
                )
            )
        self.speakers = get_spk(spk_list)
        self.default_speaker = default_spearker


        ## set tmp folder ##
        global tmp
        tmp = tmp_path
        if os.path.exists(tmp) == False:
            os.makedirs(tmp)
        
        

        ### load model ###
        self.net_g = SynthesizerTrn(
            len(symbols),
            self.hps.data.filter_length // 2 + 1,
            self.hps.train.segment_size // self.hps.data.hop_length,
            n_speakers=self.hps.data.n_speakers,
            **self.hps.model).to(self.device)
        _ = self.net_g.eval()

        _ = utils.load_checkpoint(model, self.net_g, None, skip_optimizer=True)



    def generate(self, text, speaker, sdp_ratio:float = 0.2, noise_scale:float = 0.6, noise_scale_w:float = 0.8, length_scale = 0.0):
        
        ### run bert+vits2 ###
        text = replace_string(text)
        wav_file = hashlib.md5(str(random.random()).encode()).hexdigest() + '.wav'
        speed = (100 - length_scale) / 100
        speaker = self._get_speaker(speaker)
        r_text = add_period(text)
        self._infer_long(wav_file, r_text, sdp_ratio, noise_scale, noise_scale_w, speed, speaker)
        au = f"{tmp}/{wav_file}"
        return "成功", (au)

    
    def _get_speaker(self, search_name):
        
        if search_name in self.speakers:
            return search_name
        
        else:
            return self.default_speaker


    def _infer(self, text, sdp_ratio, noise_scale, noise_scale_w, length_scale, sid):
    
        bert, phones, tones, lang_ids = get_text(text, "ZH", self.hps)
        with torch.no_grad():
            x_tst=phones.to(self.device).unsqueeze(0)
            tones=tones.to(self.device).unsqueeze(0)
            lang_ids=lang_ids.to(self.device).unsqueeze(0)
            bert = bert.to(self.device).unsqueeze(0)
            x_tst_lengths = torch.LongTensor([phones.size(0)]).to(self.device)
            del phones
            speakers = torch.LongTensor([self.hps.data.spk2id[sid]]).to(self.device)
            audio = self.net_g.infer(x_tst, x_tst_lengths, speakers, tones, lang_ids, bert, sdp_ratio=sdp_ratio
                            , noise_scale=noise_scale, noise_scale_w=noise_scale_w, length_scale=length_scale)[0][0,0].data.cpu().float().numpy()
            del x_tst, tones, lang_ids, bert, x_tst_lengths, speakers
            return audio



    def _infer_long(self, wav_n,text, sdp_ratio, noise_scale, noise_scale_w, length_scale, sid):
        slices = split_text(text)
        audio_list=[]
        with torch.no_grad():
            for slice in tqdm(slices):
                audio = self._infer(slice, sdp_ratio, noise_scale, noise_scale_w, length_scale, sid)
                audio_list.append(audio)
                silence = np.zeros(int(self.hps.data.sampling_rate * 0.2))
                audio_list.append(silence)
        audio_merged = np.concatenate(audio_list)
        sf.write(f"{tmp}/{wav_n}", audio_merged, self.hps.data.sampling_rate)
        torch.cuda.empty_cache()
        
        
        
    def play_wav(self, wav_file_path):
        import wave, pyaudio
        wf = wave.open(wav_file_path, 'rb')
        # Create a PyAudio object
        p = pyaudio.PyAudio()

        # Open a stream
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # Read data from the WAV file and play it
        data = wf.readframes(1024)
        while len(data) > 0:
            stream.write(data)
            data = wf.readframes(1024)

        # Close the stream
        stream.stop_stream()
        stream.close()

        # Terminate the PyAudio object
        p.terminate()




