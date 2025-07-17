import streamlit as st
import pandas as pd
import numpy as np

# 设置页面标题
st.title('金属冲压模具管理系统')

# 添加一个简单的介绍文本
st.write('欢迎使用金属冲压模具管理系统！这是一个使用Streamlit构建的示例应用，专注于管理金属冲压模具。')

# 创建一个简单的数据表格示例
data = pd.DataFrame({
    '模具编号': ['S001', 'S002', 'S003'],
    '模具名称': ['冲压模具A', '冲压模具B', '冲压模具C'],
    '状态': ['使用中', '维修中', '库存中'],
    '使用次数': [1200, 600, 850]
})

# 显示数据表格
st.subheader('模具信息表')
st.dataframe(data)

# 添加一个简单的图表
st.subheader('冲压模具使用统计')
chart_data = pd.DataFrame(
    np.random.randn(20, 3),
    columns=['冲压模具X', '冲压模具Y', '冲压模具Z'])

st.line_chart(chart_data)

# 添加侧边栏控件
st.sidebar.title('控制面板')
selected_option = st.sidebar.selectbox(
    '选择查看选项',
    ['全部模具', '使用中', '维修中', '库存中']
)

# 添加一些交互控件
if st.button('显示更多信息'):
    st.info('这是一个示例按钮，点击后显示更多信息。')

# 添加文件上传功能
uploaded_file = st.file_uploader('上传冲压模具数据文件', type=['csv', 'xlsx'])
if uploaded_file is not None:
    st.success('文件上传成功！')