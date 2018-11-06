#include "TF1.h"

void Double_Crystal_Ball_Fit(){
    return 0;
}

Double_t double_xtal_ball(Double_t *x, Double_t *p) {
    TF1 *f1 = new TF1("f1","crystalball"); 
    TF1 *f2 = new TF1("f2","crystalball"); 
    f1->SetParameters(p[0]/2, p[1], p[2],    p[3], p[4]);
    f2->SetParameters(p[0]/2, p[1], p[2], -1*p[3], p[4]);
    return (f1->Eval(x[0])) + (f2->Eval(x[0]));
}
