# genshin_vits2
原神鐵道對話自動語音

<br/>

本項目利用圖片文字識別擷取在遊玩原神(Genshin )和崩壞：星穹鐵道(Honkai: Star Rail )時對話內容，並利用語音模型[fishaudio/Bert-VITS2](https://github.com/fishaudio/Bert-VITS2)將對話內容根據角色轉成語音，實現對話自動配音功能。

<br/>
<br/>
<br/>
<br/>


# Install

1. 下載此庫到電腦中
```bash
git clone https://github.com/tea9296/genshin_vits2
cd genshin_vits2
```


<br/>
<br/>




2. 利用conda創建python 3.10的虛擬環境，並安裝相關套件
```bash
conda create -n py3-10 python=3.10 -y
conda activate py3-10
pip install -r requirements.txt
```

<br/>
<br/>




3. 下載[Bert-VITS2推理整合包](https://pan.ai-hobbyist.org/Models/Vits/Packs/%E5%8E%9F%E7%A5%9E&%E6%98%9F%E7%A9%B9%E9%93%81%E9%81%93%E8%AF%AD%E9%9F%B3%E5%90%88%E6%88%90_20231105.zip)，來源於[bilibili](https://www.bilibili.com/video/BV1zp4y1T7aa/?vd_source=51872a4ec45d4bb4472aa50c9fafd9ee)

<br/>


4. 需要更改檔名為.7z才能解壓縮，解壓縮完成後，將所有檔案和資料夾移到vits2/資料夾下

  ```bash
  move "原神&星穹合成_20231105.zip" "原神&星穹合成_20231105.7z"
  
  ```

<br/>
<br/>
<br/>
<br/>


# Start
1. 可更改config.json中設定，如主角語音(main_character)、預設角色語音(default_character)、截圖按鍵("key_press")。

<br/>

角色語音列表可至"vits2/models/genshin/spks.json"查看

<br/>
<br/>





2. 在遊戲中自動截圖需要系統管理原身分，因此以系統管理員身分開啟命令提示字元(cmd)，並啟動程式
```bash
conda activate py3-10
cd genshin_vits2
python main.py
```
<br/>
<br/>



3. 看到"start listening...."表示啟動成功，可以開始使用，在遊戲中欲將對話轉成語音時，按下截圖按鍵(預設截圖按鍵為"space")便會將對話文字根據角色轉成語音並播出，按下"scroll lock"鍵結束程式。

<br/>

(scroll lock鍵為Home鍵上面那顆)
<br/>
<br/>
<br/>
<br/>


4. [demo](https://youtu.be/a5nEUCBoJ44)
