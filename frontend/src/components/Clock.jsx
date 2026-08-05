import { useEffect, useState } from 'react'

/** Bangladesh Standard Time is UTC+6 year-round — no DST to account for. */
const formatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Dhaka',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

/** Live BD-time clock for the top bar, with a blinking cursor at the end. */
function Clock() {
  const [now, setNow] = useState(() => formatter.format(new Date()))

  useEffect(() => {
    const timer = setInterval(() => setNow(formatter.format(new Date())), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="navbar-clock">
      <span className="navbar-clock-label">BDT — UTC+6</span>
      <span className="navbar-clock-value">
        {now}
        <span className="blink-cursor">_</span>
      </span>
    </div>
  )
}

export default Clock
