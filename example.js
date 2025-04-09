// ==UserScript==
// @name         Deepseek Chat Exporter
// @namespace    http://tampermonkey.net/
// @version      0.3
// @description  导出Deepseek Chat对话内容为Markdown/PDF/HTML格式，支持思考过程
// @author       aka
// @match        https://*.deepseek.com/a/chat/s/*
// @match        https://*.deepseek.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      api.notion.com
// @icon         https://chat.deepseek.com/favicon.ico
// ==/UserScript==
// 用于参考的脚本，参考保存到notion

(function () {
  'use strict';

  let state = {
    targetResponse: null,
    lastUpdateTime: null,
    convertedMd: null,
    currentChatId: null,
    isCollapsed: false, // 新增状态：是否折叠
    notionConfig: {
      apiToken: GM_getValue('notionApiToken', ''),
      databaseId: GM_getValue('notionDatabaseId', '')
    }
  };

  const log = {
    info: (msg) => console.log(`[DeepSeek Exporter] ${msg}`),
    error: (msg, e) => console.error(`[DeepSeek Exporter] ${msg}`, e)
  };

  function createExportButtons() {
    const buttonContainer = document.createElement('div');
    const mdButton = document.createElement('button');
    const notionButton = document.createElement('button');
    const notionConfigButton = document.createElement('button'); // 添加Notion配置按钮
    const toggleButton = document.createElement('div');

    Object.assign(buttonContainer.style, {
      position: 'fixed',
      top: '50%',  // 垂直居中
      right: '0',
      transform: 'translateY(-50%)',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      opacity: '0.7',
      transition: 'all 0.3s ease',
      cursor: 'move',
      backdropFilter: 'blur(5px)',
      backgroundColor: 'rgba(255, 255, 255, 0.1)',
      padding: '8px',
      borderRadius: '8px 0 0 8px',
      boxShadow: '-2px 0 5px rgba(0,0,0,0.1)'
    });

    const buttonStyles = {
      padding: '10px 16px',
      backgroundColor: '#2563eb',
      color: '#ffffff',
      border: 'none',
      borderRadius: '6px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
      whiteSpace: 'nowrap',
      fontSize: '14px',
      fontWeight: '500',
      letterSpacing: '0.3px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '6px'
    };

    // 创建切换按钮的样式
    Object.assign(toggleButton.style, {
      width: '20px',
      height: '50px',
      position: 'absolute',
      left: '-20px',
      top: 'calc(50% - 25px)',
      backgroundColor: 'rgba(37, 99, 235, 0.8)',
      borderRadius: '4px 0 0 4px',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontSize: '14px',
      boxShadow: '-2px 0 5px rgba(0,0,0,0.1)'
    });
    toggleButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>';

    mdButton.onmouseenter = () => {
      Object.assign(mdButton.style, {
        backgroundColor: '#1d4ed8',
        transform: 'translateY(-1px)',
        boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)'
      });
    };

    mdButton.onmouseleave = () => {
      Object.assign(mdButton.style, buttonStyles);
    };

    // 设置Notion按钮样式
    notionButton.id = 'exportToNotionButton';
    notionButton.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4.16667 2H11.8333C12.4777 2 13 2.52233 13 3.16667V12.8333C13 13.4777 12.4777 14 11.8333 14H4.16667C3.52233 14 3 13.4777 3 12.8333V3.16667C3 2.52233 3.52233 2 4.16667 2Z" stroke="currentColor" stroke-width="1.5"/><path d="M5 5H11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M5 8H11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M5 11H9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>导出到Notion';
    Object.assign(notionButton.style, buttonStyles);

    notionButton.onmouseenter = () => {
      Object.assign(notionButton.style, {
        backgroundColor: '#1d4ed8',
        transform: 'translateY(-1px)',
        boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)'
      });
    };

    notionButton.onmouseleave = () => {
      Object.assign(notionButton.style, buttonStyles);
    };

    // 设置Notion配置按钮样式
    notionConfigButton.id = 'notionConfigButton';
    notionConfigButton.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z" stroke="currentColor" stroke-width="1.5"/></svg>';
    Object.assign(notionConfigButton.style, {
      padding: '8px',
      backgroundColor: '#4b5563',
      color: '#ffffff',
      border: 'none',
      borderRadius: '6px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    });

    notionConfigButton.onmouseenter = () => {
      Object.assign(notionConfigButton.style, {
        backgroundColor: '#374151',
        transform: 'translateY(-1px)',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
      });
    };

    notionConfigButton.onmouseleave = () => {
      Object.assign(notionConfigButton.style, {
        padding: '8px',
        backgroundColor: '#4b5563',
        color: '#ffffff',
        border: 'none',
        borderRadius: '6px',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: 'none',
        boxShadow: 'none'
      });
    };

    // 配置按钮点击打开配置界面
    notionConfigButton.onclick = function () {
      showNotionConfigModal();
    };

    mdButton.id = 'downloadMdButton';
    mdButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>导出MD';
    Object.assign(mdButton.style, buttonStyles);

    buttonContainer.onmouseenter = () => buttonContainer.style.opacity = '1';
    buttonContainer.onmouseleave = () => buttonContainer.style.opacity = '0.7';

    // 切换收缩/展开状态
    function toggleCollapse() {
      state.isCollapsed = !state.isCollapsed;

      if (state.isCollapsed) {
        buttonContainer.style.right = '-100px'; // 收缩到屏幕外
        toggleButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>';
      } else {
        buttonContainer.style.right = '0';
        toggleButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>';
      }
    }

    toggleButton.onclick = function (e) {
      e.stopPropagation();
      toggleCollapse();
    };

    let isDragging = false;
    let currentY;
    let initialY;
    let yOffset = 0;

    buttonContainer.onmousedown = dragStart;
    document.onmousemove = drag;
    document.onmouseup = dragEnd;

    function dragStart(e) {
      if (e.target === buttonContainer || e.target === toggleButton) {
        initialY = e.clientY - yOffset;
        isDragging = true;
        e.preventDefault();
      }
    }

    function drag(e) {
      if (isDragging) {
        e.preventDefault();
        currentY = e.clientY - initialY;
        yOffset = currentY;
        setTranslate(currentY, buttonContainer);
      }
    }

    function dragEnd() {
      initialY = currentY;
      isDragging = false;
    }

    function setTranslate(yPos, el) {
      const maxY = window.innerHeight - el.offsetHeight;
      const newY = Math.min(Math.max(yPos, -el.offsetHeight / 2), maxY - el.offsetHeight / 2);

      el.style.top = `calc(50% + ${newY}px)`;
    }

    mdButton.onclick = function () {
      if (!state.convertedMd) {
        alert('还没有发现有效的对话记录。\n请等待目标响应或进行一些对话。');
        return;
      }
      try {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const jsonData = JSON.parse(state.targetResponse);
        const chatName = `DeepSeek - ${jsonData.data.biz_data.chat_session.title || 'Untitled Chat'}`.replace(/[/\\?%*:|"<>]/g, '-');
        const fileName = `${chatName}_${timestamp}.md`;

        const blob = new Blob([state.convertedMd], { type: 'text/markdown' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        link.click();

        log.info(`成功下载文件: ${fileName}`);
      } catch (e) {
        log.error('下载过程中出错:', e);
        alert('下载过程中发生错误，请查看控制台了解详情。');
      }
    };

    // Notion导出按钮点击事件
    notionButton.onclick = function () {
      if (!state.convertedMd) {
        alert('还没有发现有效的对话记录。\n请等待目标响应或进行一些对话。');
        return;
      }

      // 如果没有配置Notion API，显示配置界面
      if (!state.notionConfig.apiToken || !state.notionConfig.databaseId) {
        showNotionConfigModal();
        return;
      }

      try {
        const jsonData = JSON.parse(state.targetResponse);
        const chatTitle = jsonData.data.biz_data.chat_session.title || 'Untitled Chat';
        exportToNotion(chatTitle, state.convertedMd);
      } catch (e) {
        log.error('准备导出到Notion时出错:', e);
        alert('导出到Notion过程中发生错误，请查看控制台了解详情。');
      }
    };

    buttonContainer.appendChild(mdButton);

    // 创建Notion按钮组(包含导出按钮和配置按钮)
    const notionButtonGroup = document.createElement('div');
    Object.assign(notionButtonGroup.style, {
      display: 'flex',
      gap: '6px',
      alignItems: 'center'
    });

    notionButtonGroup.appendChild(notionButton);
    notionButtonGroup.appendChild(notionConfigButton);
    buttonContainer.appendChild(notionButtonGroup);

    buttonContainer.appendChild(toggleButton);
    document.body.appendChild(buttonContainer);
  }

  // 显示Notion配置对话框
  function showNotionConfigModal() {
    // 创建模态对话框
    const modal = document.createElement('div');
    Object.assign(modal.style, {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: '10000'
    });

    // 创建对话框内容
    const modalContent = document.createElement('div');
    Object.assign(modalContent.style, {
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '10px',
      width: '400px',
      maxWidth: '90%',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      color: '#333'
    });

    modalContent.innerHTML = `
      <h3 style="margin-top:0;font-size:18px;color:#2563eb">Notion API 配置</h3>
      <p style="margin-bottom:15px;font-size:14px;line-height:1.4">要将内容直接导出到Notion，您需要提供以下信息：</p>

      <div style="margin-bottom:15px">
        <label style="display:block;margin-bottom:5px;font-size:14px;font-weight:600">Notion API Token</label>
        <input id="notionApiToken" type="password" value="${state.notionConfig.apiToken}" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;font-size:14px" />
        <p style="margin-top:5px;font-size:12px;color:#666">
          <a href="https://www.notion.so/my-integrations" target="_blank" style="color:#2563eb;text-decoration:none">创建Notion集成</a> 并获取Token
        </p>
        <p style="margin-top:5px;font-size:12px;color:#666">
          注意：请确保已将集成添加到您要导出的Notion数据库中
        </p>
      </div>

      <div style="margin-bottom:20px">
        <label style="display:block;margin-bottom:5px;font-size:14px;font-weight:600">Notion数据库ID</label>
        <input id="notionDatabaseId" type="text" value="${state.notionConfig.databaseId}" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;font-size:14px" />
        <p style="margin-top:5px;font-size:12px;color:#666">
          数据库ID是URL中https://www.notion.so/xxx?v=<b>数据库ID</b>的部分
        </p>
      </div>

      <div style="display:flex;justify-content:flex-end;gap:10px">
        <button id="cancelNotionConfig" style="padding:8px 16px;background:#f3f4f6;border:none;border-radius:4px;cursor:pointer;font-size:14px">取消</button>
        <button id="saveNotionConfig" style="padding:8px 16px;background:#2563eb;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px">保存</button>
      </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // 添加事件监听器
    document.getElementById('cancelNotionConfig').addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    document.getElementById('saveNotionConfig').addEventListener('click', () => {
      const apiToken = document.getElementById('notionApiToken').value.trim();
      const databaseId = document.getElementById('notionDatabaseId').value.trim();

      if (!apiToken) {
        alert('请输入Notion API Token');
        return;
      }

      if (!databaseId) {
        alert('请输入Notion数据库ID');
        return;
      }

      // 保存配置
      state.notionConfig = { apiToken, databaseId };
      GM_setValue('notionApiToken', apiToken);
      GM_setValue('notionDatabaseId', databaseId);

      document.body.removeChild(modal);

      // 提示保存成功
      alert('Notion配置已保存。现在您可以点击"导出到Notion"按钮将内容导出。');
    });
  }

  // 导出到Notion的函数
  function exportToNotion(title, content) {
    // 显示加载提示
    const loadingToast = document.createElement('div');
    Object.assign(loadingToast.style, {
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      padding: '10px 20px',
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      color: 'white',
      borderRadius: '4px',
      zIndex: '10000',
      fontSize: '14px'
    });
    loadingToast.textContent = '正在导出到Notion...';
    document.body.appendChild(loadingToast);

    // 将Markdown内容解析为结构化数据
    const sections = [];
    const lines = content.split('\n');
    let currentSection = { type: 'paragraph', content: [] };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // 处理标题
      if (line.startsWith('# ')) {
        if (currentSection.content.length > 0) {
          sections.push(currentSection);
        }
        sections.push({ type: 'heading_1', content: line.substring(2) });
        currentSection = { type: 'paragraph', content: [] };
      } else if (line.startsWith('## ')) {
        if (currentSection.content.length > 0) {
          sections.push(currentSection);
        }
        sections.push({ type: 'heading_2', content: line.substring(3) });
        currentSection = { type: 'paragraph', content: [] };
      } else if (line.startsWith('### ')) {
        if (currentSection.content.length > 0) {
          sections.push(currentSection);
        }
        sections.push({ type: 'heading_3', content: line.substring(4) });
        currentSection = { type: 'paragraph', content: [] };
      } else if (line === '') {
        // 处理空行：如果当前段落有内容，并且下一行不是空行，则结束当前段落
        if (currentSection.content.length > 0 && (i + 1 < lines.length && lines[i + 1].trim() !== '')) {
          sections.push(currentSection);
          currentSection = { type: 'paragraph', content: [] };
        }
      } else {
        // 普通文本行，添加到当前段落
        if (currentSection.content.length > 0) {
          // 如果不是第一行，添加换行符
          currentSection.content.push("\n" + line);
        } else {
          currentSection.content.push(line);
        }
      }
    }

    // 添加最后一个段落（如果有内容）
    if (currentSection.content.length > 0) {
      sections.push(currentSection);
    }

    // 创建Notion块，确保不超过100个
    const notionBlocks = [
      {
        object: 'block',
        type: 'paragraph',
        paragraph: {
          rich_text: [
            {
              type: 'text',
              text: {
                content: '内容已通过DeepSeek Chat Exporter导出'
              }
            }
          ]
        }
      }
    ];

    // 将sections转换为Notion blocks，合并内容以减少blocks数量
    const MAX_BLOCKS = 95; // 留一些余量
    let blockCount = 1; // 已经有一个介绍段落

    for (let i = 0; i < sections.length && blockCount < MAX_BLOCKS; i++) {
      const section = sections[i];

      if (section.type === 'paragraph') {
        notionBlocks.push({
          object: 'block',
          type: 'paragraph',
          paragraph: {
            rich_text: [
              {
                type: 'text',
                text: {
                  content: section.content.join('')
                }
              }
            ]
          }
        });
        blockCount++;
      } else if (section.type === 'heading_1') {
        notionBlocks.push({
          object: 'block',
          type: 'heading_1',
          heading_1: {
            rich_text: [
              {
                type: 'text',
                text: {
                  content: section.content
                }
              }
            ]
          }
        });
        blockCount++;
      } else if (section.type === 'heading_2') {
        notionBlocks.push({
          object: 'block',
          type: 'heading_2',
          heading_2: {
            rich_text: [
              {
                type: 'text',
                text: {
                  content: section.content
                }
              }
            ]
          }
        });
        blockCount++;
      } else if (section.type === 'heading_3') {
        notionBlocks.push({
          object: 'block',
          type: 'heading_3',
          heading_3: {
            rich_text: [
              {
                type: 'text',
                text: {
                  content: section.content
                }
              }
            ]
          }
        });
        blockCount++;
      }
    }

    // 如果内容太多，添加提示信息
    if (blockCount >= MAX_BLOCKS && sections.length > blockCount) {
      notionBlocks.push({
        object: 'block',
        type: 'paragraph',
        paragraph: {
          rich_text: [
            {
              type: 'text',
              text: {
                content: `⚠️ 由于Notion API限制，只能显示部分内容。完整内容请下载Markdown文件查看。`
              }
            }
          ]
        }
      });
    }

    // 构建Notion API请求
    GM_xmlhttpRequest({
      method: 'POST',
      url: `https://api.notion.com/v1/pages`,
      headers: {
        'Authorization': `Bearer ${state.notionConfig.apiToken}`,
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
      },
      data: JSON.stringify({
        parent: { database_id: state.notionConfig.databaseId },
        properties: {
          title: {
            title: [
              {
                text: {
                  content: title
                }
              }
            ]
          }
        },
        children: notionBlocks
      }),
      onload: function (response) {
        document.body.removeChild(loadingToast);

        if (response.status >= 200 && response.status < 300) {
          const data = JSON.parse(response.responseText);
          const successToast = document.createElement('div');
          Object.assign(successToast.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '10px 20px',
            backgroundColor: 'rgba(22, 163, 74, 0.9)',
            color: 'white',
            borderRadius: '4px',
            zIndex: '10000',
            fontSize: '14px'
          });
          successToast.textContent = '成功导出到Notion！';
          document.body.appendChild(successToast);

          // 提供链接跳转到新创建的页面
          const pageUrl = `https://notion.so/${data.id.replace(/-/g, '')}`;
          const linkElem = document.createElement('a');
          linkElem.href = pageUrl;
          linkElem.target = '_blank';
          linkElem.textContent = '打开页面';
          linkElem.style.color = 'white';
          linkElem.style.marginLeft = '10px';
          linkElem.style.textDecoration = 'underline';
          successToast.appendChild(linkElem);

          // 3秒后移除提示
          setTimeout(() => {
            if (document.body.contains(successToast)) {
              document.body.removeChild(successToast);
            }
          }, 5000);

          log.info(`成功导出到Notion: ${pageUrl}`);
        } else {
          const errorMessage = response.responseText ? JSON.parse(response.responseText).message : '未知错误';
          alert(`导出到Notion失败: ${errorMessage}`);
          log.error(`导出到Notion失败: ${response.status} - ${errorMessage}`);
        }
      },
      onerror: function (error) {
        document.body.removeChild(loadingToast);
        alert('无法连接到Notion API，请检查网络连接或API Token是否正确。\n\n您可以点击配置按钮重新设置Notion API。');
        log.error('Notion API请求错误:', error);
      }
    });
  }

  function convertJsonToMd(data) {
    let mdContent = [];
    const title = data.data.biz_data.chat_session.title || 'Untitled Chat';
    const totalTokens = data.data.biz_data.chat_messages.reduce((acc, msg) => acc + msg.accumulated_token_usage, 0);
    mdContent.push(`# DeepSeek - ${title} (Total Tokens: ${totalTokens})\n`);

    data.data.biz_data.chat_messages.forEach(msg => {
      const role = msg.role === 'USER' ? 'Human' : 'Assistant';
      mdContent.push(`### ${role}`);

      const timestamp = new Date(msg.inserted_at * 1000).toISOString();
      mdContent.push(`*${timestamp}*\n`);

      let content = msg.content;

      if (msg.search_results && msg.search_results.length > 0) {
        const citations = {};
        msg.search_results.forEach((result, index) => {
          if (result.cite_index !== null) {
            citations[result.cite_index] = result.url;
          }
        });
        content = content.replace(/\[citation:(\d+)\]/g, (match, p1) => {
          const url = citations[parseInt(p1)];
          return url ? ` [${p1}](${url})` : match;
        });
        content = content.replace(/\s+,/g, ',').replace(/\s+\./g, '.');
      }

      if (msg.thinking_content) {
        const thinkingTime = msg.thinking_elapsed_secs ? `(${msg.thinking_elapsed_secs}s)` : '';
        content += `\n\n**Thinking Process ${thinkingTime}:**\n${msg.thinking_content}`;
      }

      content = content.replace(/\$\$(.*?)\$\$/gs, (match, formula) => {
        return formula.includes('\n') ? `\n$$\n${formula}\n$$\n` : `$$${formula}$$`;
      });

      mdContent.push(content + '\n');
    });

    return mdContent.join('\n');
  }

  function processTargetResponse(text, url) {
    try {
      const chatId = url.match(/chat_session_id=([^&]+)/)?.[1];
      if (!chatId) {
        log.error('无法从URL中提取chat_session_id');
        return;
      }

      if (state.currentChatId !== chatId) {
        state.currentChatId = chatId;
        state.targetResponse = null;
        state.convertedMd = null;
        log.info(`检测到对话切换，已清空缓存数据 (${chatId})`);
      }

      state.targetResponse = text;
      state.lastUpdateTime = new Date().toLocaleTimeString();
      log.info(`成功捕获目标响应 (${text.length} bytes) 来自: ${url}`);

      state.convertedMd = convertJsonToMd(JSON.parse(text));
      log.info('成功将JSON转换为Markdown');
    } catch (e) {
      log.error('处理目标响应时出错:', e);
    }
  }

  const hookXHR = () => {
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (...args) {
      if (args[1] && typeof args[1] === 'string' && args[1].includes('history_messages?chat_session_id') && args[1].includes('&cache_version=')) {
        args[1] = args[1].split('&cache_version=')[0];
      }
      this.addEventListener('load', function () {
        if (this.responseURL && this.responseURL.includes('history_messages?chat_session_id')) {
          processTargetResponse(this.responseText, this.responseURL);
        }
      });
      originalOpen.apply(this, args);
    };
  };
  hookXHR();

  window.addEventListener('load', function () {
    createExportButtons();

    const observer = new MutationObserver(() => {
      if (!document.getElementById('downloadMdButton')) {
        log.info('检测到按钮丢失，正在重新创建...');
        createExportButtons();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    log.info('DeepSeek导出脚本已启动');
  });
})();