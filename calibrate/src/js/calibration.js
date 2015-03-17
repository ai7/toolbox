// Raymond's display calibration JS code

// global obj for tracking and updating the colors
var gColor = function() {

   // protected by closure
   var r = 1;
   var g = 1;
   var b = 1;
   var l = 100;

   // returns an object with these methods that can be used
   // to update the above closure variables
   return {
      
      // return string like "rgb(90%, 90%, 90%)"
      getColor: function() {
         var sr = (r ? l : '0') + '%';
         var sg = (g ? l : '0') + '%';
         var sb = (b ? l : '0') + '%';
         return "rgb(" + sr + ", " + sg + ", " + sb + ")";
      },

      // turn individual color on/off
      flipRed: function()   { 
         r = r ? 0: 1; 
      },
      flipGreen: function() { 
         g = g ? 0: 1; 
      },
      flipBlue: function()  { 
         b = b ? 0: 1; 
      },
      
      // set level to the specific value
      setLevel: function(level) {
         l = level;
      },
      // increase level by 10%, will wrap around if at 100%
      incLevel: function() { 
         l = (l + 10) % 110; 
      },
      // decrease level by 10%, will wrap around if at 0%
      decLevel: function() {
         if (l == 0) {
            l = 100;
         } else {
            l = (l - 10) % 110;
         }
      }
   }

}(); // IIFE


// update the background color and status text
function updateBackground() {
   // change the background color
   var color = gColor.getColor();
   document.body.style.background = color;
   // write the new color info to the status text
   updateStatusInfo(color);
}


// update the status text
function updateStatusInfo(color) {
   var width = screen.width;
   var height = screen.height;
   var depth = screen.colorDepth;
   var rText = width + ' x ' + height;
   var dText = ' [ ' + depth + ' bpp ]';
   document.getElementById("footer").innerHTML = color + '<br>' + rText + dText;
}


// keyboard event handler
function doc_keyUp(e) {
   var redraw = true;
   switch (e.keyCode) {
      case 48: // 0
         gColor.setLevel(0);
         break;
      case 49: // 1
         gColor.setLevel(10);
         break;
      case 50: // 2
         gColor.setLevel(20);
         break;
      case 51: // 3
         gColor.setLevel(30);
         break;
      case 52: // 4
         gColor.setLevel(40);
         break;
      case 53: // 5
         gColor.setLevel(50);
         break;
      case 54: // 6
         gColor.setLevel(60);
         break;
      case 55: // 7
         gColor.setLevel(70);
         break;
      case 56: // 8
         gColor.setLevel(80);
         break;
      case 57: // 9
         gColor.setLevel(90);
         break;
      case 65: // a
         gColor.setLevel(100);
         break;
      case 82: // r
         gColor.flipRed();
         break;
      case 71: // g
         gColor.flipGreen();
         break;
      case 66: // b
         gColor.flipBlue();
         break;
      case 32: // space
      case 39: // right arrow
         gColor.incLevel();
         break;
      case 37: // left arrow
         gColor.decLevel();
         break;
      case 70: // f
         requestFullScreen(e.target);
         redraw = false;
         break;
      default:
         redraw = false;
         break;
   }
   if (redraw) {
      updateBackground();
   }
}


function requestFullScreen(element)
{
   // Supports most browsers and their versions.
   var requestMethod = (element.requestFullScreen ||
                        element.webkitRequestFullScreen ||
                        element.mozRequestFullScreen ||
                        element.msRequestFullscreen);

   if (requestMethod) { // Native full screen.
      requestMethod.call(element);
   } else if (typeof window.ActiveXObject !== "undefined") { // Older IE.
      var wscript = new ActiveXObject("WScript.Shell");
      if (wscript !== null) {
         wscript.SendKeys("{F11}");
      }
   }
}

function main()
{
   // register keyboard handler
   document.addEventListener('keyup', doc_keyUp, false);
}

/*
function main()
{
}
*/

// start of script, run main() when page is ready
document.addEventListener("DOMContentLoaded", main, false);
