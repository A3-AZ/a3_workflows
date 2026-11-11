#include "script_component.hpp"

// Comments may contain anything: ( [ { 	
/* block comment ( [ {
   still a comment */
class CfgPatches {
    class ADDON {
        name = "Example (good)";
        units[] = {};
        requiredAddons[] = {"cba_main"};
    };
};

class CfgVehicles {
    class Man;
    class CAManBase: Man {
        displayName = "Text with ) ] } and 'quotes'";
    };
};
