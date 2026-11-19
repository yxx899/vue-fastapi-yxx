import { h } from 'vue'
import { ElMessageBox } from 'element-plus'

/** 伤心脸吉祥物（与问答页同款形象，嘴角下弯） */
function SadMascot() {
  return h(
    'svg',
    {
      viewBox: '0 0 120 120',
      xmlns: 'http://www.w3.org/2000/svg',
      class: 'logout-sad-mascot',
      'aria-hidden': 'true',
    },
    [
      h('defs', null, [
        h(
          'linearGradient',
          { id: 'logoutMascotBody', x1: '20', y1: '20', x2: '100', y2: '110', gradientUnits: 'userSpaceOnUse' },
          [h('stop', { stopColor: '#7dd3fc' }), h('stop', { offset: '1', stopColor: '#0284c7' })],
        ),
        h('linearGradient', { id: 'logoutMascotCheek', x1: '0', y1: '0', x2: '1', y2: '1' }, [
          h('stop', { stopColor: '#fda4af' }),
          h('stop', { offset: '1', stopColor: '#fb7185' }),
        ]),
      ]),
      h('ellipse', { cx: '60', cy: '108', rx: '34', ry: '6', fill: 'rgba(2,132,199,0.18)' }),
      h('circle', { cx: '60', cy: '62', r: '38', fill: 'url(#logoutMascotBody)' }),
      h('path', { d: 'M28 48c-6-18 8-30 18-18', fill: '#38bdf8' }),
      h('path', { d: 'M92 48c6-18-8-30-18-18', fill: '#38bdf8' }),
      h('path', { d: 'M31 47c-3-10 4-16 10-9', fill: '#e0f2fe' }),
      h('path', { d: 'M89 47c3-10-4-16-10-9', fill: '#e0f2fe' }),
      h('ellipse', { cx: '60', cy: '66', rx: '28', ry: '24', fill: '#f0f9ff' }),
      h('circle', { cx: '48', cy: '64', r: '5.5', fill: '#0f2744' }),
      h('circle', { cx: '72', cy: '64', r: '5.5', fill: '#0f2744' }),
      h('circle', { cx: '49.8', cy: '62.2', r: '1.8', fill: '#fff' }),
      h('circle', { cx: '73.8', cy: '62.2', r: '1.8', fill: '#fff' }),
      h('path', {
        d: 'M42 72c0 3 2.2 5 4 5s4-2 4-5c0-2.2-2-5-4-5s-4 2.8-4 5z',
        fill: '#7dd3fc',
        opacity: '0.95',
      }),
      h('circle', { cx: '40', cy: '74', r: '4.5', fill: 'url(#logoutMascotCheek)', opacity: '0.75' }),
      h('circle', { cx: '80', cy: '74', r: '4.5', fill: 'url(#logoutMascotCheek)', opacity: '0.75' }),
      h('path', {
        d: 'M50 82c4-5 16-5 20 0',
        fill: 'none',
        stroke: '#0369a1',
        strokeWidth: '2.4',
        strokeLinecap: 'round',
      }),
      h('rect', {
        x: '78',
        y: '86',
        width: '22',
        height: '16',
        rx: '3',
        fill: '#fff',
        stroke: '#0284c7',
        strokeWidth: '1.5',
      }),
      h('path', { d: 'M89 86v16', stroke: '#0284c7', strokeWidth: '1.2' }),
      h('path', { d: 'M82 91h6M82 95h6', stroke: '#7dd3fc', strokeWidth: '1.4', strokeLinecap: 'round' }),
    ],
  )
}

/**
 * 退出登录防误触确认。
 * @returns {Promise<boolean>} 用户点确定为 true，取消/关闭为 false
 */
export async function confirmLogout() {
  try {
    await ElMessageBox({
      title: '',
      message: h('div', { class: 'logout-confirm-body' }, [
        h(SadMascot),
        h('p', { class: 'logout-confirm-text' }, '你真的要离开我吗？'),
      ]),
      showCancelButton: true,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      customClass: 'logout-confirm-box',
      center: true,
      closeOnClickModal: false,
      distinguishCancelAndClose: true,
    })
    return true
  } catch {
    return false
  }
}
