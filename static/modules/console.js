/**
 * console demo
 */




layui.define(function(exports){
  
  /*
    下面通过 layui.use 分段加载不同的模块，实现不同区域的同时渲染，从而保证视图的快速呈现
  */
  
  
  //区块轮播切换
  layui.use(['admin', 'carousel'], function(){
    var $ = layui.$
    ,admin = layui.admin
    ,carousel = layui.carousel
    ,element = layui.element
    ,device = layui.device();

    //轮播切换
    $('.layadmin-carousel').each(function(){
      var othis = $(this);
      carousel.render({
        elem: this
        ,width: '100%'
        ,arrow: 'none'
        ,interval: othis.data('interval')
        ,autoplay: othis.data('autoplay') === true
        ,trigger: (device.ios || device.android) ? 'click' : 'hover'
        ,anim: othis.data('anim')
      });
    });
    
    element.render('progress');
    
  });



  //数据概览
  layui.use(['admin', 'carousel', 'echarts'], function(){
    var $ = layui.$
    ,admin = layui.admin
    ,carousel = layui.carousel
    ,echarts = layui.echarts;
    
    var echartsApp = [], options = [
      //今日流量趋势
      {
        title: {
          text: '最近24小时流量趋势',
          x: 'center',
          textStyle: {
            fontSize: 14
          }
        },
        tooltip : {
          trigger: 'axis'
        },
        legend: {
          data:['','']
        },
        xAxis : [{
          type : 'category',
          boundaryGap : false,
          data: []
        }],
        yAxis : [{
          type : 'value'
        }],
        series : [{
          name:'发送',
          type:'line',
          smooth:true,
          itemStyle: {normal: {areaStyle: {type: 'default'}}},
          data: []
        },{
          name:'接收',
          type:'line',
          smooth:true,
          itemStyle: {normal: {areaStyle: {type: 'default'}}},
          data: []
        }]
      },
      

      
      //新增的用户量
      {
        title: {
          text: '最近一周新增的用户量',
          x: 'center',
          textStyle: {
            fontSize: 14
          }
        },
        tooltip : { //提示框
          trigger: 'axis',
          formatter: "{b}<br>新增用户：{c}"
        },
        xAxis : [{ //X轴
          type : 'category',
          data : ['11-07', '11-08', '11-09', '11-10', '11-11', '11-12', '11-13']
        }],
        yAxis : [{  //Y轴
          type : 'value'
        }],
        series : [{ //内容
          type: 'line',
          data:[200, 300, 400, 610, 150, 270, 380],
        }]
      }
    ]
    ,elemDataView = $('#LAY-index-dataview').children('div')
    ,renderDataView = function(index){
      echartsApp[index] = echarts.init(elemDataView[index], layui.echartsTheme);
      echartsApp[index].setOption(options[index]);
      // window.onresize = echartsApp[index].resize;
      admin.resize(function(){
        echartsApp[index].resize();
      });
    };


    
    //没找到DOM，终止执行
    if(!elemDataView[0]) return;
    
    
    
    //renderDataView(0);
    
    //触发数据概览轮播
    var carouselIndex = 0;
    carousel.on('change(LAY-index-dataview)', function(obj){
      renderDataView(carouselIndex = obj.index);
    });
    
    //触发侧边伸缩
    layui.admin.on('side', function(){
      setTimeout(function(){
        renderDataView(carouselIndex);
      }, 300);
    });
    
    //触发路由
    layui.admin.on('hash(tab)', function(){
      layui.router().path.join('') || renderDataView(carouselIndex);
    });



    function generateLast24Hours() {
      let result = [];
      for (let i = 23; i >= 0; i--) {
        let date = new Date();
        date.setHours(date.getHours() - i);
        result.push(date.getHours());
      }
      return result;
    }
    


    function reloadData(){
      // 添加 jQuery 的 ajax 请求来获取新数据并更新今日流量趋势的数据
      $.ajax({
        url:'/api/system/data_usage',
        type: 'get',
        dataType: 'json',
        success: function(res) {
          options[0].series[0].data = Object.values(res.sent);  // 更新 sent 数据
          options[0].series[1].data = Object.values(res.recv);  // 更新 recv 数据
          options[0].xAxis[0].data = Object.values(generateLast24Hours());  // 更新 recv 数据

          renderDataView(0);  // 重新渲染图表
        },
        error: function(error) {
          console.error('获取数据出错:', error);
        }
      });
    }
    //加载数据
    reloadData()



    

  });



  //地图
  layui.use(['carousel', 'echarts'], function(){
    var $ = layui.$
    ,carousel = layui.carousel
    ,echarts = layui.echarts;
    
    var echartsApp = [], options = [
      {
        title : {
          text: '服务器地区分布',
          subtext: '敬请期待更多服务器'
        },
        tooltip : {
          trigger: 'item'
        },
        dataRange: {
          orient: 'horizontal',
          min: 0,
          max: 300,
          text:['高','低'],
          splitNumber:0
        },
        series : [
          { 
            name: '访客地区分布',
            type: 'map',
            mapType: 'china',    
            selectedMode : 'multiple',
            itemStyle:{
                normal:{label:{show:true}},
                emphasis:{label:{show:true}}
            },
            data:[
                {name:'西藏', value:0},
                {name:'青海', value:0},
                {name:'宁夏', value:0},
                {name:'海南', value:0},
                {name:'甘肃', value:0},
                {name:'贵州', value:0},
                {name:'新疆', value:0},
                {name:'云南', value:0},
                {name:'重庆', value:0},
                {name:'吉林', value:0},
                {name:'山西', value:0},
                {name:'天津', value:0},
                {name:'江西', value:0},
                {name:'广西', value:0},
                {name:'陕西', value:0},
                {name:'黑龙江', value:0},
                {name:'内蒙古', value:0},
                {name:'安徽', value:0},
                {name:'北京', value:0},
                {name:'福建', value:0},
                {name:'上海', value:0},
                {name:'湖北', value:0},
                {name:'湖南', value:0},
                {name:'四川', value:200},
                {name:'辽宁', value:0},
                {name:'河北', value:0},
                {name:'河南', value:0},
                {name:'浙江', value:200},
                {name:'山东', value:0},
                {name:'江苏', value:0},
                {name:'广东', value:0}
            ]
          }
        ]
      }
    ]
    ,elemDataView = $('#LAY-index-pagethree-home').children('div')
    ,renderDataView = function(index){
      echartsApp[index] = echarts.init(elemDataView[index], layui.echartsTheme);
      echartsApp[index].setOption(options[index]);
      window.onresize = echartsApp[index].resize;
    }; 
    //没找到DOM，终止执行
    if(!elemDataView[0]) return;
 
    renderDataView(0);  
  });

  //最新订单
  layui.use('table', function(){
    var $ = layui.$
    ,table = layui.table;
    
    //今日热搜
    table.render({
      elem: '#LAY-index-topSearch'
      ,url: layui.setter.paths.base + 'json/console/top-search.js' //模拟接口
      ,page: true
      ,cols: [[
        {type: 'numbers', fixed: 'left'}
        ,{field: 'keywords', title: '关键词', minWidth: 300, templet: '<div><a href="https://www.baidu.com/s?wd={{ d.keywords }}" target="_blank" class="layui-table-link">{{ d.keywords }}</div>'}
        ,{field: 'frequency', title: '搜索次数', minWidth: 120, sort: true}
        ,{field: 'userNums', title: '用户数', sort: true}
      ]]
      ,skin: 'line'
    });
    
    //今日热贴
    table.render({
      elem: '#LAY-index-topCard'
      ,url: layui.setter.paths.base + 'json/console/top-card.js' //模拟接口
      ,page: true
      ,cellMinWidth: 120
      ,cols: [[
        {type: 'numbers', fixed: 'left'}
        ,{field: 'title', title: '标题', minWidth: 300, templet: '<div><a href="{{ d.href }}" target="_blank" class="layui-table-link">{{ d.title }}</div>'}
        ,{field: 'username', title: '发帖者'}
        ,{field: 'channel', title: '类别'}
        ,{field: 'crt', title: '点击率', sort: true}
      ]]
      ,skin: 'line'
    });

    //项目进展
    table.render({
      elem: '#LAY-home-homepage-console'
      ,url: layui.setter.paths.base + 'json/console/prograss.js' //模拟接口
      ,cols: [[
        {type: 'checkbox', fixed: 'left'}
        ,{field: 'prograss', title: '任务'}
        ,{field: 'time', title: '所需时间'}
        ,{field: 'complete', title: '完成情况'
          ,templet: function(d){
            if(d.complete == '已完成'){
              return '<del style="color: #16b777;">'+ d.complete +'</del>'
            }else if(d.complete == '进行中'){
              return '<span style="color: #FFB800;">'+ d.complete +'</span>'
            }else{
              return '<span style="color: #FF5722;">'+ d.complete +'</span>'
            }
          }
        }
      ]]
      ,skin: 'line'
    });

  });
  
  exports('console', {})
});