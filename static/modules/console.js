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


//最新订单
  layui.use('table', function(){
    var $ = layui.$
    ,table = layui.table;
    

layui.use(['table', 'jquery', 'layer'], function(){
  var table = layui.table;
  var $ = layui.jquery;

  // 今日热贴 - 前端分页实现
  // 1. 手动发起AJAX请求，获取全部数据
  $.get('/api/node/topNodes', function(res) {
    // 2. 检查数据是否获取成功
    if (res && res.code === '0' && res.data && res.data.length > 0) {
      // 3. 渲染表格，直接将获取到的数据传给 data 参数
      table.render({
        elem: '#LAY-index-topCard',
        data: res.data,                // 核心：使用已获取的完整数据
        page: true,                    // 开启分页
        limit: 10,                     // 每页显示10条
        limits: [10, 20, 30, 50],      // 可选的每页数量
        cellMinWidth: 120,
        cols: [[
          {type: 'numbers', fixed: 'left'},
          {field: 'name', title: '用户名', minWidth: 200, sort: true},
          {field: 'online', title: '在线节点', sort: true},
          {field: 'nodes', title: '累计节点', sort: true},
          {field: 'routes', title: '路由数量', sort: true}
        ]],
        skin: 'line',
        // 注意：这里不需要 url 参数了
      });
    } else {
      // 数据为空或请求失败
      table.render({
        elem: '#LAY-index-topCard',
        data: [],
        page: false,
        cols: [[
          {type: 'numbers', fixed: 'left'},
          {field: 'name', title: '用户名', minWidth: 200},
          {field: 'online', title: '在线节点'},
          {field: 'nodes', title: '累计节点'},
          {field: 'routes', title: '路由数量'}
        ]],
        skin: 'line'
      });
      layer.msg(res.msg || '暂无数据', {icon: 7});
    }
  }).fail(function() {
    layer.msg('网络错误，无法获取数据', {icon: 5});
  });
});



  });
    

  
  
  exports('console', {})
});