let heritageItems = [];
let selectedHeritageItem = null;

export const setHeritageItems = (items) => { heritageItems = items; };
export const getHeritageItems = () => heritageItems;
export const setSelectedHeritageItem = (item) => { selectedHeritageItem = item; };
export const getSelectedHeritageItem = () => selectedHeritageItem;
