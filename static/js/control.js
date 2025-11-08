function expandCollapseNav(elem) {
    const displaySetting = elem.nextElementSibling.style.display;
    let newDisplaySetting = (displaySetting == 'none') ? "block" : "none";
    let newPlusMinus = (displaySetting == 'none') ? "-" : "+";
    elem.nextElementSibling.style.display = newDisplaySetting;
    elem.querySelector("span").innerHTML = newPlusMinus;
}