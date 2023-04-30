## cryptopaper  &nbsp;&nbsp;  :chart_with_upwards_trend: ![#StandWithUkraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraineFlat.svg) :newspaper:
<img src="https://user-images.githubusercontent.com/6677966/235366423-d989484c-08c7-4d56-8ca0-e36e3fbf1434.png" width="50%" height="50%" align="right" />

**A BTC/LTC/USD dashboard with scraped headlines, topical statistics and data from on-going global crises.**


Designed with high-visibility and at-a-glance updates in mind.  Intended for 2200x1650 e-paper devices such as the Boox Mira.  Well suited to low power instrumentation.


**&lt;UP&gt;** and **&lt;DOWN&gt;** keys will adjust contrast

**&lt;ESC&gt;** to exit


### From left to right from top to bottom:
- Time, Date, BTC/USD Spot
- Headlines from BBC world news*
- BTC/USD high and low during the last six hours**
- Main BTC/USD chart for the last six hours.**
- Versatile Data Chart
    
    Currently shows statistics from Russia's brutal, destructive and entirely self-inflicted death-spiral. Was going to be climate data but ended up being used to show Covid-19 stats instead. Then Putin went on TV and told everyone, "I have decided..."
- Movement Indicator
    
    At a glance you can see whether BTC/USD is currently (relative to the six hour window) trending upwards or downards. It's a simplified high/low candle adapted for high visibility.

<img src="https://user-images.githubusercontent.com/6677966/234790110-400add24-bf82-4109-b8a9-505b3fcef9c7.png" width="20%" height="20%" align="right" />

- Volatility Indicator
    
    If the inner circle fills the outer circle, there's been around 10% movement (or more) during the last six hours**.  It's a high visibility indicator of the scale of the movement seen during the six hour window. 
    
    Spread and change for this period are also shown above and below on its right hand side.
 
    This is also where you'll find the digital clock's analogue second hand.

- Weather, Status, LTC/USD
    
    Current weather, Configured locale, local IP, contrast level (if not default), uptime & LTC/USD
    
<img src="https://user-images.githubusercontent.com/6677966/233832158-7e42e4ac-bd03-4369-b225-5c6c31f826ad.png" width="20%" height="20%" align="right" />

- LTC/BTC rate** will remain 'inverted' if below a preset threshold.
<br/><br/>

\* _Headlines will flash (alternating inverted state) if they match any of a set of words defined in lib/watch-words.txt._

\** _Chart will need six hours from launch to fill with data as no files are written to or saved at any point._

---

### Customizations:

- Watch Words

    <b>lib/watch-words.txt</b> contains an editable list of newline-separated search strings.
    
    Any headline containing any of these strings will flash (toggling inverted status every other second).
    
- Options

    <b>lib/options.txt</b> contains two editable values; one for LTC/BTC threshold and one for the weather search string i.e. your location.
    
    Below the LTC/BTC threshold specified in this file, the LTC/BTC indicator will be inverted (white on black).
    The weather locale is fed to the most excellent [wttr.in](https://github.com/chubin/wttr.in) so location strings valid there should work here.
    
- Versatile Data Chart

    Currently the data is pulled from the [2022-Ukraine-Russia-War-Dataset](https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset).
    The plan is to abstract this into a plug-in module so it's more... versatile.
    
---

<img src="https://user-images.githubusercontent.com/6677966/233561264-787c6f9b-b217-4bd5-b1ed-eb5739ab9676.png" width="20%" height="20%" align="right" />

### Notes:

&nbsp;&nbsp;&nbsp;&nbsp;This little project was never intended for public consumption, but I found it so useful that it kept getting hacked into a slightly better version until eventually it felt like something I should share. Maybe someone will want to tweak the files and run it on a Pi with a nice e-paper display like I do; maybe I've saved someone ten minutes because they can pinch some code or ideas.  In any case, enjoy.  
&nbsp;&nbsp;&nbsp;&nbsp;Oh, and Slava Ukraini.
    
    
  
