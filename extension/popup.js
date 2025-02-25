// 當頁面載入時初始化
document.addEventListener('DOMContentLoaded', async function() {
  // 1. 立即載入儲存的郵件地址
  loadSavedEmails();
  
  // 2. 添加輸入事件監聽器
  const ownerEmailInput = document.getElementById('ownerEmail');
  const memberEmailsInput = document.getElementById('memberEmails');

  ownerEmailInput.addEventListener('input', function() {
    saveEmails(this.value, memberEmailsInput.value);
  });

  memberEmailsInput.addEventListener('input', function() {
    saveEmails(ownerEmailInput.value, this.value);
  });

  // 3. 獲取並顯示 JIRA issues
  const issuesList = document.getElementById('issuesList');
  const selectAll = document.getElementById('selectAll');
  
  try {
    // 首先檢查 JIRA 登入狀態
    const checkLoginResponse = await fetch('https://jira.realtek.com/rest/auth/1/session', {
      method: 'GET',
      credentials: 'include'
    });

    if (!checkLoginResponse.ok) {
      issuesList.innerHTML = `
        <div class="error">
          Please connect to VPN first and login to JIRA<br>
          <small>Note: External access to JIRA has been disabled since Oct 21, 2024</small><br>
          <a href="https://jira.realtek.com/" target="_blank">Click here to login JIRA</a><br>
          <small>If you have VPN issues, please contact HelpDesk (#17885)</small>
        </div>`;
      return;
    }

    // 獲取設定的 URL
    const settings = await new Promise(resolve => {
      chrome.storage.sync.get({
        'jiraXmlUrl': 'https://jira.realtek.com/sr/jira.issueviews:searchrequest-xml/59583/SearchRequest-59583.xml?tempMax=1000'
      }, resolve);
    });

    // 嘗試獲取 XML
    const response = await fetch(settings.jiraXmlUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/xml',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        issuesList.innerHTML = `
          <div class="error">
            No access to JIRA XML view.<br>
            Please connect to VPN first and login to JIRA<br>
            <small>Note: External access to JIRA has been disabled since Oct 21, 2024</small><br>
            <a href="https://jira.realtek.com/" target="_blank">Click here to login JIRA</a><br>
            <small>If you have VPN issues, please contact HelpDesk (#17885)</small>
          </div>`;
      } else {
        issuesList.innerHTML = `
          <div class="error">
            Error accessing JIRA: ${response.status}<br>
            Please check your JIRA XML URL in settings
          </div>`;
      }
      return;
    }

    const text = await response.text();
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(text, 'text/xml');
    
    const issues = [];
    const items = xmlDoc.getElementsByTagName('item');
    const total = items.length;
    let processed = 0;
    
    // 在開始載入時顯示進度
    issuesList.innerHTML = '<div class="loading">Loading and filtering issues...</div>';

    // 載入設定
    chrome.storage.sync.get({
      'commentHours': 18,  // 預設值為 18
      'targetUsers': 'JIRAUSER50632,JIRAUSER51966'  // 預設值
    }, function(result) {
      document.getElementById('commentHours').value = result.commentHours;
      document.getElementById('targetUsers').value = result.targetUsers;
    });

    // 2. 獲取每個 issue 的評論
    for (const item of items) {
      const key = item.getElementsByTagName('key')[0]?.textContent;
      const title = item.getElementsByTagName('title')[0]?.textContent;
      const link = item.getElementsByTagName('link')[0]?.textContent;
      
      try {
        // 更新進度顯示
        processed++;
        issuesList.innerHTML = `<div class="loading">Processing issues... (${processed}/${total})</div>`;
        
        // 獲取 issue 詳細資訊
        const issueDetails = await getIssueDetails(key);
        
        // 獲取 issue 的評論
        const commentsResponse = await fetch(`https://jira.realtek.com/rest/api/2/issue/${key}/comment`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        if (!commentsResponse.ok) {
          console.error(`Failed to fetch comments for ${key}`);
          continue;
        }
        
        const commentsData = await commentsResponse.json();
        const comments = commentsData.comments || [];
        
        // 獲取設定
        const settings = await new Promise(resolve => {
          chrome.storage.sync.get({
            'commentHours': 18,  // 預設值
            'targetUsers': 'JIRAUSER50632,JIRAUSER51966'  // 預設值
          }, resolve);
        });

        const targetUsers = settings.targetUsers.split(',').map(u => u.trim());

        // 找出指定用戶的最後一則評論
        let lastTargetUserComment = null;

        // 從後往前找，這樣可以更快找到最後的評論
        for (let i = comments.length - 1; i >= 0; i--) {
          const comment = comments[i];
          if (targetUsers.includes(comment.author.key)) {
            lastTargetUserComment = comment;
            break;
          }
        }

        // 如果找到指定用戶的評論
        if (lastTargetUserComment) {
          const commentCreated = new Date(lastTargetUserComment.created);
          const now = new Date();
          const hoursDiff = (now - commentCreated) / (1000 * 60 * 60);
          
          // 只檢查時間條件
          if (hoursDiff <= settings.commentHours) {
            issues.push({
              title,
              link,
              key,
              assignee: issueDetails.assigneeName,
              assigneeEmail: issueDetails.assigneeEmail,
              lastComment: {
                author: lastTargetUserComment.author.key,
                created: commentCreated,
                body: lastTargetUserComment.body
              }
            });
          }
        }
      } catch (error) {
        console.error(`Error processing issue ${key}:`, error);
      }
    }

    // 3. 顯示符合條件的 issues
    if (issues.length === 0) {
      issuesList.innerHTML = '<div class="loading">No matching issues found</div>';
      return;
    }

    issuesList.innerHTML = issues.map((issue, index) => `
      <div class="issue-item">
        <input type="checkbox" class="issue-checkbox" data-index="${index}">
        <div class="issue-content">
          <div class="issue-title">
            <a href="${issue.link}" target="_blank">${issue.title}</a>
          </div>
          <div class="issue-assignee">
            Assignee: ${issue.assignee || 'Unassigned'}
            ${issue.assigneeEmail ? `<span class="assignee-email">(${issue.assigneeEmail})</span>` : ''}
          </div>
          <div class="issue-comment">
            target user comment: ${issue.lastComment.author} 
            (${new Date(issue.lastComment.created).toLocaleString()})
          </div>
        </div>
      </div>
    `).join('');

    // 設置全選功能
    selectAll.addEventListener('change', function() {
      document.querySelectorAll('.issue-checkbox').forEach(checkbox => {
        checkbox.checked = this.checked;
      });
    });

    // 在顯示 issues 的部分添加更新數量的函數
    function updateIssueCount() {
      const total = document.querySelectorAll('.issue-item').length;
      const selected = document.querySelectorAll('.issue-item input[type="checkbox"]:checked').length;
      document.getElementById('issueCount').textContent = `(${selected}/${total})`;
    }

    // 添加事件監聽器
    document.querySelectorAll('.issue-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', updateIssueCount);
    });

    // 修改 selectAll 的事件處理
    document.getElementById('selectAll').addEventListener('change', function() {
      const checkboxes = document.querySelectorAll('.issue-checkbox');
      checkboxes.forEach(cb => {
        cb.checked = this.checked;
      });
      updateIssueCount();
    });

    // 初始更新數量
    updateIssueCount();

  } catch (error) {
    console.error('Error:', error);
    issuesList.innerHTML = `
      <div class="error">
        Error: ${error.message}<br>
        Please connect to VPN first and login to JIRA<br>
        <small>Note: External access to JIRA has been disabled since Oct 21, 2024</small><br>
        <a href="https://jira.realtek.com/" target="_blank">Click here to login JIRA</a><br>
        <small>If you have VPN issues, please contact HelpDesk (#17885)</small>
      </div>`;
  }
});

document.getElementById('createChat').addEventListener('click', function() {
  const selectedIssues = Array.from(document.querySelectorAll('.issue-checkbox:checked'))
    .map(checkbox => {
      const index = parseInt(checkbox.dataset.index);
      const container = checkbox.closest('.issue-item');
      const titleElement = container.querySelector('.issue-title a');
      const assigneeElement = container.querySelector('.issue-assignee');
      
      return {
        title: titleElement.textContent.trim(),
        link: titleElement.href,
        key: titleElement.href.split('/').pop(),
        assignee: assigneeElement.textContent.replace('Assignee:', '').split('(')[0].trim(),
        assigneeEmail: container.querySelector('.assignee-email')?.textContent.replace(/[()]/g, '')
      };
    });

  if (selectedIssues.length === 0) {
    alert('Please select at least one issue');
    return;
  }

  const status = document.getElementById('status');
  status.style.display = 'block';
  status.className = '';
  status.textContent = 'Creating chats...';

  const ownerEmail = document.getElementById('ownerEmail').value;
  const memberEmails = document.getElementById('memberEmails').value
    .split('\n')
    .map(email => email.trim())
    .filter(email => email);

  // 直接發送請求
  chrome.runtime.sendNativeMessage('com.realtek.teams_chat',
    {
      action: 'createSelectedChats',
      selectedIssues,
      ownerEmail,
      memberEmails
    },
    function(response) {
      console.log('Attempting to send message to native host...');
      
      if (chrome.runtime.lastError) {
        console.error('Native messaging error:', chrome.runtime.lastError);
        status.className = 'error';
        status.textContent = `Native messaging error: ${chrome.runtime.lastError.message}`;
        return;
      }

      if (response && response.success) {
        status.className = 'success';
        let successMessage = 'Chats created successfully!';
        if (Array.isArray(response.result)) {
          successMessage += '<br><br>Created chats:';
          response.result.forEach(chat => {
            successMessage += `<br>- ${chat.name}`;
            if (chat.webUrl) {
              successMessage += ` <a href="${chat.webUrl}" target="_blank">Open</a>`;
            }
          });
        }
        status.innerHTML = successMessage;
      } else {
        status.className = 'error';
        status.textContent = response 
          ? `Error: ${response.message}` 
          : 'Failed to create chats';
      }
    }
  );
});

// 添加一個函數來處理批量創建聊天
async function createChatsFromIssues(issues) {
  const status = document.getElementById('status');
  const ownerEmail = document.getElementById('ownerEmail').value;
  const memberEmailsStr = document.getElementById('memberEmails').value;
  const memberEmails = memberEmailsStr.split(',').map(email => email.trim());
  
  // 儲存當前輸入的郵件地址
  saveEmails(ownerEmail, memberEmailsStr);
  
  status.style.display = 'block';
  status.className = '';
  
  for (const issue of issues) {
    status.textContent = `Creating chat for issue: ${issue.title}...`;
    
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendNativeMessage('com.realtek.teams_chat',
          {
            action: "createSelectedChats",
            selectedIssues: [{
              title: issue.title,
              link: issue.link,
              key: issue.key,
              assignee: issue.assignee,
              assigneeEmail: issue.assigneeEmail
            }],
            ownerEmail: ownerEmail,
            memberEmails: memberEmails
          },
          function(response) {
            if (chrome.runtime.lastError) {
              reject(chrome.runtime.lastError);
            } else {
              resolve(response);
            }
          }
        );
      });

      if (response && response.success) {
        status.className = 'success';
        let successMessage = `Chat created for: ${issue.title}`;
        if (response.result && response.result.webUrl) {
          successMessage += `<br><a href="${response.result.webUrl}" target="_blank">Open in Teams</a>`;
        }
        status.innerHTML = successMessage;
        
        // 等待一段時間再創建下一個
        await new Promise(resolve => setTimeout(resolve, 2000));
      } else {
        throw new Error(response ? response.message : 'Failed to create chat');
      }
    } catch (error) {
      status.className = 'error';
      status.innerHTML = `Error creating chat for ${issue.title}: ${error.message}`;
      // 等待一段時間後繼續
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  status.className = 'success';
  status.textContent = 'All chats created!';
}

// 設置相關代碼
document.getElementById('settingsBtn').addEventListener('click', function() {
  document.getElementById('modalBackdrop').style.display = 'block';
  document.getElementById('settingsModal').style.display = 'block';
  
  // 載入已保存的設置
  chrome.storage.sync.get({
    'jiraToken': '',
    'jiraUsername': '',
    'commentHours': 18,
    'targetUsers': 'JIRAUSER50632,JIRAUSER51966',
    'jiraXmlUrl': 'https://jira.realtek.com/sr/jira.issueviews:searchrequest-xml/59583/SearchRequest-59583.xml?tempMax=1000'
  }, function(result) {
    document.getElementById('jiraToken').value = result.jiraToken;
    document.getElementById('jiraUsername').value = result.jiraUsername;
    document.getElementById('commentHours').value = result.commentHours;
    document.getElementById('targetUsers').value = result.targetUsers;
    document.getElementById('jiraXmlUrl').value = result.jiraXmlUrl;
  });
});

document.getElementById('closeSettings').addEventListener('click', function() {
  document.getElementById('modalBackdrop').style.display = 'none';
  document.getElementById('settingsModal').style.display = 'none';
});

document.getElementById('saveSettings').addEventListener('click', function() {
  const token = document.getElementById('jiraToken').value;
  const username = document.getElementById('jiraUsername').value;
  const hours = parseInt(document.getElementById('commentHours').value) || 18;
  const users = document.getElementById('targetUsers').value;
  const xmlUrl = document.getElementById('jiraXmlUrl').value;
  
  chrome.storage.sync.set({
    jiraToken: token,
    jiraUsername: username,
    commentHours: hours,
    targetUsers: users,
    jiraXmlUrl: xmlUrl
  }, function() {
    document.getElementById('modalBackdrop').style.display = 'none';
    document.getElementById('settingsModal').style.display = 'none';
    // 重新載入 issues 列表
    location.reload();
  });
});

// 獲取 Issue 詳細資訊的函數
async function getIssueDetails(issueKey) {
  const credentials = await new Promise(resolve => {
    chrome.storage.sync.get(['jiraToken', 'jiraUsername'], resolve);
  });
  
  if (!credentials.jiraToken || !credentials.jiraUsername) {
    throw new Error('Please set JIRA credentials in settings');
  }
  
  const response = await fetch(`https://jira.realtek.com/rest/api/2/issue/${issueKey}`, {
    method: 'GET',
    headers: {
      'Authorization': 'Basic ' + btoa(`${credentials.jiraUsername}:${credentials.jiraToken}`),
      'Accept': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch issue details: ${response.status}`);
  }
  
  const data = await response.json();
  return {
    assigneeEmail: data.fields.assignee?.emailAddress,
    assigneeName: data.fields.assignee?.displayName
  };
}

function saveEmails(ownerEmail, memberEmails) {
    if (ownerEmail || memberEmails) {  // 只要有一個有值就儲存
        chrome.storage.sync.set({
            'lastOwnerEmail': ownerEmail,
            'lastMemberEmails': memberEmails
        }, function() {
            console.log('Emails saved successfully');
        });
    }
}

function loadSavedEmails() {
    chrome.storage.sync.get(['lastOwnerEmail', 'lastMemberEmails'], function(result) {
        const ownerEmailInput = document.getElementById('ownerEmail');
        const memberEmailsInput = document.getElementById('memberEmails');
        
        if (result.lastOwnerEmail && !ownerEmailInput.value) {
            ownerEmailInput.value = result.lastOwnerEmail;
        }
        if (result.lastMemberEmails && !memberEmailsInput.value) {
            memberEmailsInput.value = result.lastMemberEmails;
        }
    });
} 