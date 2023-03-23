# pyodbc経由でIRISに接続するlambda関数を作成するまでの流れ
参考にしたAWSドキュメント：https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/lambda-python.html

このリポジトリでご紹介する手順は以下の通りです。

1. [レイヤーを作成する](#1-レイヤーを作成する)
2. [Lambda関数を作成する](#2-lambda関数を追加する)
3. [1,2の流れをCloudformationで行う例](#3-12の流れをcloudformationで行う例)

## 事前準備

- EC2インスタンスを用意し（例ではUbuntu20.04）IRISをインストールした環境を用意し、IRISのスーパーサーバーポート（1972番）にアクセスできるようにします。

- IRISに以下テーブルとデータを用意しておく（USERネームスペースで作成する例）

  IRISにログインします。  
  ```
  iris session iris
  ```
  続いて、SQL用シェルに切り替え（:sql）、CREATE文とINSERT文を実行します。

  ```
  :sql
  CREATE TABLE Test.Person (Name VARCHAR(50),Email VARCHAR(50))

  INSERT INTO Test.Person (Name,Email) VALUES('山田','taro@mai.com')
  INSERT INTO Test.Person (Name,Email) VALUES('武田','takeda@mai.com')
  ```
  SQLシェルを終了するには `quit` を入力します。

  ```
  quit
  ```
  IRISからログアウトするには、`halt`コマンドを使用します。
  ```
  halt
  ```

- Lambda関数からEC2にアクセスするときのロールを作成しておく

  《参考にしたページ》https://dev.classmethod.jp/articles/tsnote-lambda-the-provided-execution-role-does-not-have-permissions-to-call-createnetworkinterface-on-ec2/


## 1. レイヤーを作成する

《参考にしたページ》https://qiita.com/Todate/items/03c5d3911b52b93d39af

レイヤーは、Lambda関数で使用するライブラリとその他依存関係ファイルをZipファイルでアーカイブしたもので、コードやデータも含めることができるそうですが、この説明では、IRISの接続に必要なunixODBC用ファイル、pyodbcモジュール用ファイルを含めたレイヤ―作成の流れでご紹介します。

>ご参考：[レイヤーについてのドキュメント](https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/configuration-layers.html?icmpid=docs_lambda_help)


- [(1) unixODBC用soファイルの用意](#1-unixodbc用soファイルの用意)
- [(2) IRIS用ドライバのダウンロード](#2-iris用ドライバのダウンロード)
- [(3) pyodbcのインストール](#3-pyodbcのインストール)
- [(4) ODBCデータソース用ファイルの作成](#4-odbcデータソース用ファイルの作成)
- [(5) zip作成（レイヤーの作成）](#5-zip作成レイヤーの作成)
- [(6) レイヤーの追加](#6-レイヤーの追加)


### (1) unixODBC用soファイルの用意

unixODBC-2.3.7 の soファイルを入手するため、以下ページを参考にしています。

https://qiita.com/Todate/items/03c5d3911b52b93d39af

以下任意ディレクトリ上で実行します。
```
curl ftp://ftp.unixodbc.org/pub/unixODBC/unixODBC-2.3.7.tar.gz -O
tar xvzf unixODBC-2.3.7.tar.gz
cd unixODBC-2.3.7
./configure --sysconfdir=/opt --disable-gui --disable-drivers --enable-iconv --with-iconv-char-enc=UTF8 --with-iconv-ucode-enc=UTF16LE --prefix=/opt
make
sudo make install
```

ここまでで /opt/lib/*.so　ができるので、libディレクトリをレイヤー作成用ディレクトリに全コピーします。

以降、レイヤー作成用ディレクトリを `~/pyodbc_lambda` として記述します。

```
sudo cp -r /opt/lib ~/pyodbc_lambda/
```

### (2) IRIS用ドライバのダウンロード

IRIS用ドライバ[libirisodbcur6435.so](https://github.com/Intersystems-jp/IRISModules/blob/master/python/wheel/linux/libirisodbcur6435.so)をレイヤー作成用ディレクトリ以下`lib`ディレクトリにダウンロードします。

```
cd ~/pyodbc_lambda/lib
wget https://github.com/Intersystems-jp/IRISModules/raw/master/python/wheel/linux/libirisodbcur6435.so
```

### (3) pyodbcのインストール

lambda関数で使用するPythonモジュールは、レイヤー内`python`ディレクトリ以下に配置します。

```
cd ~/pyodbc_lambda
mkdir python
cd python
pip3 install pyodbc -t .
```

### (4) ODBCデータソース用ファイルの作成

[`odbc.ini`](/examples/odbc.ini)と[`odbcinst.ini`](/examples/odbcinst.ini)を、レイヤー作成用ディレクトリ以下`python`ディレクトリに配置します。

レイヤー用ディレクトリ以下にあるファイルは以下の通りです。
```
$ tree
.
├── lib
│   ├── libirisodbcur6435.so
│   ├── libodbc.la
│   ├── libodbc.so -> libodbc.so.2.0.0
│   ├── libodbc.so.2 -> libodbc.so.2.0.0
│   ├── libodbc.so.2.0.0
│   ├── libodbccr.la
│   ├── libodbccr.so -> libodbccr.so.2.0.0
│   ├── libodbccr.so.2 -> libodbccr.so.2.0.0
│   ├── libodbccr.so.2.0.0
│   ├── libodbcinst.la
│   ├── libodbcinst.so -> libodbcinst.so.2.0.0
│   ├── libodbcinst.so.2 -> libodbcinst.so.2.0.0
│   ├── libodbcinst.so.2.0.0
│   └── pkgconfig
│       ├── odbc.pc
│       ├── odbccr.pc
│       └── odbcinst.pc
└── python
    ├── odbc.ini
    ├── odbcinst.ini
    ├── pyodbc-4.0.35.dist-info
    │   ├── INSTALLER
    │   ├── LICENSE.txt
    │   ├── METADATA
    │   ├── RECORD
    │   ├── WHEEL
    │   └── top_level.txt
    ├── pyodbc.cpython-38-x86_64-linux-gnu.so
    └── pyodbc.pyi

4 directories, 26 files
```


### (5) zip作成（レイヤーの作成）

レイヤー用ディレクトリで以下実行します。

```
cd ~/pyodbc_lambda
zip -r9 ../iris_pyodbc_lambda.zip *
```

ご参考：この手順で作ったZipの例 [iris_pyodbc_lambda.zip](iris_pyodbc_lambda.zip)


### (6) レイヤーの追加

[AWS Lambda](https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/discover)でレイヤーを追加します。

図例では、レイヤーの動作するアーキテクチャに `x86_64` を指定し、ランタイムに `Python3.8` を選択しています。

![](/assets/Layer-create.png)

以上でレイヤーの作成が完了です。

次はいよいよ、lambda関数の作成です。

___

## 2. Lambda関数を追加する

以下の順序で追加します。

- [(1) 確認：IRISへの接続情報について](#1-確認irisへの接続情報について)
- [(2) 確認：Lambda関数ハンドラー名について](#2-確認lambda関数ハンドラー名について)
- [(3) Lambda関数の追加](#3-lambda関数の追加)
- [(4) 環境変数の追加](#4-環境変数の追加)
- [(5) ランタイム設定の変更](#5-ランタイム設定の変更)
- [(6) レイヤーの追加](#6-レイヤーの追加)
- [(7) コード類のアップロード](#7-コード類のアップロード)
- [(8) テスト実行](#8-テスト実行)

サンプルのpythonスクリプト：[index.py](/examples/index.py)を使用して登録します。

### (1) 確認：IRISへの接続情報について
サンプルのpythonスクリプト：[index.py](/examples/index.py)では、以下いずれかの方法でIRISに接続できるように記述しています。

- 環境変数を使用する

  [index.py](./examples/index.py)には、lambda関数作成時に設定する環境変数を利用するように記述しています（18～22行目）

  （環境変数は、Lambda関数登録後、画面で設定できます。）  

- [connection.config](./examples/connection.config) を使用する

  [index.py](./examples/index.py) の9～15行目のコメントを外し18～22行をコメント化して利用します。

  接続するIRISの情報に合わせて[connection.config](./examples/connection.config)を変更してください。


### (2) 確認：Lambda関数ハンドラー名について

サンプルのpythonスクリプト：[index.py](/examples/index.py)6行目に記載の関数 `lambda_handler` を今回登録するLambda関数ハンドラーとして設定します。

Lambda関数登録時のハンドラー名として、 `"ファイルの名称"."Pythonの関数名称"`
とするルールがあるため、今回登録するハンドラー名は、`index.lambda_hander` となります。

### (3) Lambda関数の追加

[AWS Lambdaの関数](https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/functions)メニューから登録します。

図例では、関数が動作するアーキテクチャに `x86_64` を指定し、ランタイムに `Python3.8` を選択しています。

Lambda関数がEC2にアクセスできるようにする作成するロール名を指定するため、事前にロールをご準備ください。

※ロール作成の参考ページ：https://dev.classmethod.jp/articles/tsnote-lambda-the-provided-execution-role-does-not-have-permissions-to-call-createnetworkinterface-on-ec2/

![](/assets/LambdaFunction-Create.png)


### (4) 環境変数の追加

作成した関数の設定タブ：環境変数 で、`ODBCSYSINI` に `./` を設定します。

![](/assets/LambdaFunction-Environment.png)


この他、IRISへの接続情報に環境変数を利用する場合は以下追加します。

環境変数名|値
--|--
IRISHOST|13.231.153.242
IRISPORT|1972
NAMESPACE|USER
USERNAME|SuperUser
PASSWORD|SYS

例）
![](/assets/LambdaFunction-Environment-iris.png)

### (5) ランタイム設定の変更

サンプルのpythonスクリプト：[index.py]を実行時に使用したいので、ハンドラ名をデフォルト名称`lambda_function.lambda_handler`から `index.lambda_handler` に変更します。

コードタブを選択し画面下のほうにある「ランタイム設定」の「編集」をクリックして変更保存します。

![](/assets/LambdaFunction-Runtime.png)

### (6) レイヤーの追加

[レイヤーを作成する](#1-レイヤーを作成する) の手順で作成したレイヤーをLambda関数に追加します。

コードタブを選択した状態で画面一番下の「レイヤー」から「レイヤーの追加」ボタンで追加します。

![](/assets//LambdaFunction-AddLayer.png)

### (7) コード類のアップロード

以下のファイルをZipファイルに含めてアップロードします。
- [connection.config](./examples/connection.config) (IRISへの接続情報を記載したファイル)
- [index.py](./examples/index.py) 
- [odbcinst.ini](/examples/odbcinst.ini)

※IRISへ接続情報を環境変数から取得する場合は、[connection.config](./examples/connection.config)は不要です。

ご参考：[iris_pyodbc_code.zip](/iris_pyodbc_code.zip)

コードタブの右端のボタン「アップロード元」をクリックし、Zipを選択してアップロードします。

![](/assets/LambdaFunction-CodeUpload.png)

### (8) テスト実行

テストタブを使用します。

新しいイベントを作成します。（何度もテストする場合は保存しておくと便利です）

サンプルは特に引数入力がないので、指定する引数は`{}`と指定していますが、引数がある場合はJSONできるようです。
![](/assets/lambda-testnew.png)

接続ができ、SELECT文が実行できると以下のような結果を表示します。

画面上には実行した関数の戻り値の表示（JSON配列）

画面下のほうにスクリプト内で記述したprint()の結果が表示されています。
![](/assets/lambda-result.png)

___

## 3. 1,2の流れをCloudformationで行う例

サンプル：[cloudformation.xml](/cloudformation.yml)を使用して「[1. レイヤーを作成する](#1-レイヤーを作成する) 」と「[2. Lambda関数を作成する](#2-lambda関数を追加する)」の流れを自動化します。


「[1. レイヤーを作成する](#1-レイヤーを作成する)」 の流れで作成したZip（例：[iris_pyodbc_lambda.zip](iris_pyodbc_lambda.zip)）と、「[2. Lambda関数を作成する](#2-lambda関数を追加する)」 の流れで作成したZip（例：[iris_pyodbc_code.zip](/iris_pyodbc_code.zip)）を [cloudformation.xml](/cloudformation.yml) の中で指定します。

### S3にZipを配置する

S3のバケットを作成し、作成したZipファイル（例：iris_pyodbc_lambda2.zip）を配置します。

バケット名：iijimas3　にコピーしている例

```
aws s3 cp iris_pyodbc_lambda.zip s3://iijimas3
aws s3 cp iris_pyodbc_code.zip s3://iijimas3
```

※ AWS CLI https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/getting-started-install.html


### cloudformationを使ってlambda関数作成

例）[cloudformation.yml](cloudformation.yml)

ymlでは、lambda関数で使用するレイヤーの作成（リソース名：`LambdaLayer`）と、
```
    LambdaLayer:
      Type: AWS::Lambda::LayerVersion
      Properties:
        CompatibleArchitectures:
          - x86_64
        CompatibleRuntimes:
          - python3.8
        Content:
          S3Bucket: iijimas3
          S3Key: iris_pyodbc_lambda.zip
        Description: "iris python layer"
        LayerName: "IRISPyODBCLayer"
```

lambda関数を作成しています。
```
    IRISPyODBCFunction:
      Type: "AWS::Lambda::Function"
      Properties:
        Environment:
          Variables:
            IRISHOST: "13.231.153.242"
            IRISPORT: "1972"
            NAMESPACE: "USER"
            USERNAME: "SuperUser"
            PASSWORD: "SYS"
            ODBCSYSINI: "./"
        Code:
          S3Bucket: iijimas3
          S3Key: iris_pyodbc_code.zip
        Description: "IRIS pyodbc Function"
        FunctionName: iris-pyodbc
        Handler: "index.lambda_handler"
        Layers:
          - !Ref LambdaLayer
        MemorySize: 128
        Role: "arn:aws:iam::109671571309:role/lambda_vpc_basic_execution_IRIS"
        Runtime: "python3.8"
        Timeout: 30
```

lambda関数の中で使用する環境変数の設定や、
```
      Properties:
        Environment:
          Variables:
            IRISHOST: "13.231.153.242"
            IRISPORT: "1972"
            NAMESPACE: "USER"
            USERNAME: "SuperUser"
            PASSWORD: "SYS"
            ODBCSYSINI: "./"
```
関数が使用するレイヤーの指定
```
        Layers:
          - !Ref LambdaLayer
```
ハンドラー名の指定
```
        Handler: "index.lambda_handler"
```
Lambda関数がEC2にアクセスできるようにする作成するロール名の指定を行っています。

※ロール作成の参考ページ：https://dev.classmethod.jp/articles/tsnote-lambda-the-provided-execution-role-does-not-have-permissions-to-call-createnetworkinterface-on-ec2/

```
        Role: "arn:aws:iam::109671571309:role/lambda_vpc_basic_execution_IRIS"
```

※各設定値を適宜変更してください。

後は、cloudformationの画面でスタックを作成し、ymlを実行するだけです。

ymlのアップロード手順は以下の通りです。

https://ap-northeast-1.console.aws.amazon.com/cloudformation/home?region=ap-northeast-1#/

![](/assets/CreatingStack1.png)

[cloudformation.yml](cloudformation.yml)をアップロードし、スタック名を任意に決定します。

![](/assets/CreatingStack2.png)

この後2画面表示されますが、すべてデフォルトで「次へ」と「送信」ボタンをクリックします。

正しく作成できるとこの表示になります。
![](/assets/CreatingStack3.png)



作成したスタックの画面の「リソース」タブをクリックすると、lambda関数へのリンクが表示されます。

![](/assets/LambdaTest-Cloudformation.png)

テスト実行が成功すると以下のような出力が表示されます。
![](/assets/lambda-result.png)


接続できない場合は、環境変数の値をご確認ください（「設定」タブで確認できます）。
![](/assets/lambda-env-Cloudformation.png)
