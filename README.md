# haire-airbox

FORK了海尔空气盒子接入homeassistant，并传到github，方便协同修改

代码来源： https://bbs.hassbian.com/thread-9234-1-1.html
作者： zxl_hass

# 联网

海尔已经放弃了这个产品，app也无法再使用，看了 [IOS源码](https://github.com/ybyao07/airbox) 发现是 EasyLink，根据芯片查到了方案，用了[芯片商提供的IOS示例程序=》完整UI的示例程序](https://mxchip.yuque.com/books/share/8ac5e519-671d-4444-a93d-20e0aadfc793/wac2mm#easylink%E7%A4%BA%E4%BE%8Bapp%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E) 成功配网

注意：

1. 测试了IOS 15.2.1无法正常安装示例程序，没辙了就将代码重新编译了并安装到手机，可以正常使用
2. 安卓版示例程序无法选择协议，会出现无反应
3. IOS程序配网时，需要选择Mode，可能是V2，也可能是Plus，测试了一次成功就没再测试


# Changelog

1. Fork 版本 2021年9月18日
2. 增加pm2.5 (评论区回复的，作者：tjsyk https://bbs.hassbian.com/forum.php?mod=redirect&goto=findpost&ptid=9234&pid=337656)
3. 填入配网方法