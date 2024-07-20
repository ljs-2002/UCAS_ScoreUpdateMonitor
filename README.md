# Score Update Monitor
- 中国科学院大学本科成绩/绩点更新检测脚本，定时检测成绩/绩点更新并发送提醒。
- 测试环境为**python 3.9**，不确定其它环境是否支持。
- Windows下已提供一键部署的Release，无需python环境即可使用。



## 程序配置

- 所有平台都具有的基本文件结构及基本配置过程如下：

  1. 打开`./config/userInfo.json`文件，在`userName`字段填入登陆`SEP`的用户名，在`password`字段填入登陆`SEP`的密码；

     - 这两个字段用于模拟登陆；
  2. 首次使用/若上次登陆sep时使用的浏览器与之前使用的浏览器不同/手动登陆sep时出现了重新认证提示，请打开`./config/config.json`文件，修改**User-Agent**字段为最新的浏览器User-Agent。并使用浏览器先完成认证后再使用。
     - 附获取浏览器User-Agent的方法：在浏览器地址栏输入**about:version**，打开的页面中的**用户代理**，或**User-Agent**，或**UA**即为所需User-Agent。
  3. （选做）为了实现成绩/绩点更新时发送提醒功能，使用了[Server酱](https://sct.ftqq.com/)提供的微信提醒API，用户需要扫码登陆后在**Key&API**界面复制**SendKey**，并填写到`./config/userInfo.json`文件的`apikey`字段；

     - 若不填写`apikey`字段，则不会收到成绩/绩点更新的提醒，用户可以在`./log/log.txt`中查看更新情况；
     - 该API截止目前（2023/07/23）每天都有免费的发送额度，正常情况下不会给用户造成任何支出；

     - 后续考虑推出邮件提醒方式和短信提醒方式，但是考虑到配置邮件服务器的过程可能较为复杂，短信发送平台成本较高，还是推荐使用微信提醒API；

  ```
  .
  │
  ├─assets
  │      favicon.ico
  │
  ├─config
  │      userInfo.json
  │      config.json
  │
  ├─log
  │      log.txt
  │
  ├─module
  │      charsets.json
  │      sep.onnx
  │
  └─tmp
          cur_score.json
  ```

- **注意：**`./conifg/config.json`中可以配置各个过程的url，若查询接口变化可以通过该文件进行配置。

- 接着根据平台不同继续进行配置：

  - [Windows平台](#windows)
  - [Linux平台](#linux)
  - [MAC平台](#mac)

  

### Windows

- 在`Releases`中提供了`exe`文件，无需配置`python`环境即可使用。

- 文件结构及配置过程如下

  1. 右键`config.ps1`，选择**使用 PowerShell 运行**，`config.ps1`会根据当前路径配置`UCASScoreUpdateMonitor.xml`文件；
     - **若该步骤运行失败**可以直接打开`UCASScoreUpdateMonitor.xml`文件并将文件中`__command_file__`处替换为`ScoreUpdateMonitor.bat`文件的绝对路径，将`__working_dir__`处替换为`ScoreUpdateMonitor.bat`文件所在的文件夹的绝对路径；

  2. 右键`reg.bat`选择**以管理员身份运行**，`reg.bat`会自动将检测更新程序注册为任务计划程序，并在用户每次解锁电脑时触发，之后间隔一天触发一次，若中途有解锁则会刷新间隔；
     - **若该步骤失败**可以打开Windows的任务计划程序，选择**导入任务**，通过`UCASScoreUpdateMonitor.xml`文件导入任务；
     - 导入成功后会产生名为`UCASScoreUpdateMonitor`的任务，用户可以根据自己的需要自行定义任务触发的事件，每次任务触发即为检测一次更新；
  3. 按照所有平台基本配置过程**设置自己的User-Agent**；
  
  - 至此，程序的配置完成。
  
  ```
  .
  │  config.ps1
  │  README.md
  │  reg.bat
  │  ScoreUpdateMonitor.bat
  │  ScoreUpdateMonitor.exe
  │  UCASScoreUpdateMonitor.xml
  │
  ├─assets
  │      favicon.ico
  │
  ├─config
  │      userInfo.json
  │      config.json
  │
  ├─log
  │      log.txt
  │
  ├─module
  │      charsets.json
  │      sep.onnx
  │
  └─tmp
          cur_score.json
  ```



###  Linux

- 目前唯一的方法是安装依赖并定时运行`main.py`。

  - 使用下列方法安装依赖：

    ```shell
    python -m pip install -r requirements.txt
    ```

  - Linux下设置定时运行的方式**请自行搜索**。

- 文件结构如下

  ```
  .
  │  main.py
  │  README.md
  │
  ├─assets
  │      favicon.ico
  │
  ├─config
  │      userInfo.json
  │      config.json
  │
  ├─log
  │      log.txt
  │
  ├─module
  │      charsets.json
  │      sep.onnx
  │
  ├─src
  │      score_update_logger.py
  │      score_update_monitor.py
  │
  └─tmp
          cur_score.json
  ```
  
  

### MAC

- 与Linux类似。



## 运行输出

- 若配置了`apikey`

  - 当检测到成绩更新时，会将成绩更新后SEP上显示的绩点及排名以及更新的科目与对应成绩发送到API的公众号上，标题为**Score Update Monitor: Score Update**；

  - 当检测到绩点更新时，会将SEP上更新后的绩点及排名发送到API的公众号上，标题为**Score Update Monitor: GPA Update**；
  - 当检测出现错误时，会将报错信息发送到API的公众号上，标题为**Score Update Monitor: Error**;

- 运行时产生的日志在`./log/log.txt`中；



## TODO

- [ ] 实现邮件通知和短信通知
- [ ] 实现Linux一键配置
- [ ] 实现MAC一键配置
- [ ] 使用github action实现打包和预发布
- [ ] ...



## 问题反馈

- 在使用中遇到问题，请提交[Issue](https://github.com/ljs-2002/UCAS_ScoreUpdateMonitor/issues)。



## 更新

- 2023/07/23：增加实时GPA计算
- 2023/07/23：修复中期退课的课程分数为空，在计算GPA时引发异常的bug
- 2024/07/20：更新相关接口，修复SEP新增的新设备登陆认证导致的模拟登陆失败问题