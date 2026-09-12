// -*- coding: utf-8 -*-
/**
 * 行程PDF导出工具：每天一页，简洁风格。
 * 所有文字通过html2canvas渲染为图片，避免jsPDF中文字体乱码。
 */
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

/**
 * 将行程详情导出为PDF，每天一页。
 * @param tripTitle 行程标题
 * @param dayElements 每天的DOM元素数组（按天顺序）
 * @param filename 文件名
 */
export async function exportTripToPDF(
  tripTitle: string,
  dayElements: HTMLElement[],
  filename: string,
): Promise<void> {
  if (!dayElements.length) return

  const pdf = new jsPDF('p', 'mm', 'a4')
  const pageWidth = 210 // A4宽度mm
  const pageHeight = 297 // A4高度mm

  // 创建隐藏的PDF渲染容器
  const renderContainer = document.createElement('div')
  renderContainer.style.cssText = `
    position: fixed;
    left: -9999px;
    top: 0;
    width: 794px; /* A4宽度 @96dpi */
    background: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  `
  document.body.appendChild(renderContainer)

  try {
    for (let i = 0; i < dayElements.length; i++) {
      const el = dayElements[i]

      // 构建单页HTML：页眉 + 内容 + 页脚
      const pageDiv = document.createElement('div')
      pageDiv.style.cssText = `
        width: 794px;
        padding: 30px 36px;
        box-sizing: border-box;
        background: #ffffff;
      `

      // 页眉
      const header = document.createElement('div')
      header.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 12px;
        border-bottom: 1px solid #e4e3dd;
        margin-bottom: 16px;
      `
      header.innerHTML = `
        <span style="font-size: 18px; font-weight: 700; color: #1a1b1c;">${tripTitle}</span>
        <span style="font-size: 12px; color: #6b7280;">第 ${i + 1} / ${dayElements.length} 页</span>
      `
      pageDiv.appendChild(header)

      // 内容（克隆当天元素，去掉交互按钮样式影响）
      const contentWrapper = document.createElement('div')
      contentWrapper.style.cssText = `
        width: 100%;
        overflow: hidden;
      `
      const cloned = el.cloneNode(true) as HTMLElement
      // 移除可能影响渲染的交互元素
      cloned.querySelectorAll('.node-ops, .poi-picker, .position-picker').forEach(n => n.remove())
      contentWrapper.appendChild(cloned)
      pageDiv.appendChild(contentWrapper)

      // 页脚
      const footer = document.createElement('div')
      footer.style.cssText = `
        margin-top: 20px;
        padding-top: 10px;
        border-top: 1px solid #e4e3dd;
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #9ca3af;
      `
      footer.innerHTML = `
        <span>途迹 TripCanvas</span>
        <span>生成时间：${new Date().toLocaleDateString('zh-CN')}</span>
      `
      pageDiv.appendChild(footer)

      renderContainer.innerHTML = ''
      renderContainer.appendChild(pageDiv)

      // 等待渲染
      await new Promise(resolve => setTimeout(resolve, 50))

      // 渲染整页为图片
      const canvas = await html2canvas(pageDiv, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
        logging: false,
        width: 794,
      })

      const imgData = canvas.toDataURL('image/jpeg', 0.92)
      const imgWidth = pageWidth
      const imgHeight = (canvas.height * imgWidth) / canvas.width

      // 如果不是第一页，添加新页
      if (i > 0) {
        pdf.addPage()
      }

      // 计算缩放：如果内容超过页面高度，等比缩放
      let finalHeight = imgHeight
      if (imgHeight > pageHeight) {
        finalHeight = pageHeight
      }
      pdf.addImage(imgData, 'JPEG', 0, 0, imgWidth, finalHeight)
    }

    pdf.save(filename)
  } finally {
    document.body.removeChild(renderContainer)
  }
}

/**
 * 生成长截图海报（简洁风格）。
 * @param element 要截图的DOM元素
 * @returns base64图片
 */
export async function generatePoster(element: HTMLElement): Promise<string> {
  const canvas = await html2canvas(element, {
    scale: 2,
    useCORS: true,
    backgroundColor: '#f4f6f5',
    logging: false,
  })
  return canvas.toDataURL('image/jpeg', 0.92)
}
