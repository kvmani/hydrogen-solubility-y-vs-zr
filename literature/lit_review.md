# Literature Review Map (Living)

This document is the working evidence map for the Y-vs-Zr hydrogen solubility project. Each item includes DOI and a short annotation describing how it constrains model-building.

## 1) Experimental solubility / terminal solid solubility data for H in alpha-Y and alpha-Zr

- **gulbransen1955_alpha_zr**: *Solubility and Decomposition Pressures of Hydrogen in Alpha-Zirconium*. DOI: 10.1007/BF03377469  
  Foundational alpha-Zr solubility and decomposition-pressure dataset. Provides early quantitative anchors for dilute-to-precipitation behavior. Useful for initial TSS-vs-T benchmarking and sanity checks on modeled chemical potentials.

- **brown1961_oxygen_tss**: *Effect of dissolved oxygen on terminal solubility of H in alpha-Zr*. DOI: 10.1016/0022-3115(61)90156-8  
  Shows impurity sensitivity of apparent TSS in alpha-Zr. Critical for separating intrinsic Zr-H thermodynamics from impurity-modified datasets when building a defensible baseline comparison with Y.

- **sawatzky1967_thermal_diffusion**: *Hydrogen solubility in zirconium alloys by thermal diffusion*. DOI: 10.1016/0022-3115(67)90048-7  
  Provides experimentally extracted solubility trends and highlights composition effects in Zr-based systems. Useful as contextual evidence for expected low-solubility behavior on the Zr side.

- **ricca1967_equilibrium_pressures**: *Equilibrium pressures of H dissolved in alpha-Zr*. DOI: 10.1021/J100870A044  
  Connects dissolved hydrogen concentration to equilibrium gas pressure. Directly relevant for translating computed solution energetics into concentration-pressure-temperature relationships.

- **ricca1967_thermodynamic_properties**: *Thermodynamic properties of H and D in alpha-Zr*. DOI: 10.1021/J100870A045  
  Extracts thermodynamic quantities for interstitial hydrogen isotopes in alpha-Zr. Useful for validating enthalpy/entropy trends in the thermodynamic model stage.

- **hall1945_solubility_zr**: *Solubility of hydrogen in zirconium and zirconium-oxygen solid solutions*. DOI: 10.1039/TF9454100306  
  Classic primary source with isotherm/isobar data and explicit room-temperature saturation values. Useful for anchoring historical Zr-H solubility behavior and oxygen sensitivity context.

- **maeda1993_diffusivity_solubility_y**: *Diffusivity and solubility of H/D in yttrium*. DOI: 10.1039/FT9938904375  
  Key experimental source for hydrogen behavior in Y, including solubility-relevant measurements. Provides the main experimental anchor for alpha-Y-side calibration and comparison.

- **maeda1994_concentration_effects_y**: *Concentration effects on H isotope solubility/diffusivity in Y*. DOI: 10.1039/FT9949001979  
  Extends the Y dataset by quantifying concentration dependence. Important for checking where dilute assumptions begin to break and for selecting model-valid concentration windows.

Where to find TSS-vs-T anchors for modeling: start with `gulbransen1955_alpha_zr`, `ricca1967_equilibrium_pressures`, `ricca1967_thermodynamic_properties`, and reconcile with phase-assessment sources in Section 2.

## 2) Y-H and Zr-H phase diagrams and hydride structures (reliable sources)

- **khatamian1988_hy_phase_diagram**: *The H-Y system*. DOI: 10.1007/BF02881276  
  Core phase-diagram assessment for hydrogen-yttrium. Defines phase fields and transitions needed to delimit dilute alpha-Y conditions from hydride-dominated regimes.

- **zuzek1990_hzr_phase_diagram**: *The H-Zr system*. DOI: 10.1007/BF02843318  
  Canonical phase-diagram assessment for Zr-H. Essential for identifying TSS boundaries and hydride phase competition during model validation.

- **okamoto2006_hzr_update**: *H-Zr update note*. DOI: 10.1361/154770306X136638  
  Concise update to H-Zr assessment. Useful for checking later refinements relative to older assessments before adopting benchmark curves.

- **predel_hy_landolt**: *Landolt-Bornstein H-Y*. DOI: 10.1007/10501684_1567  
  Authoritative compiled database entry. Good for cross-checking phase and thermodynamic data provenance and for identifying legacy data sources.

- **predel_hzr_landolt**: *Landolt-Bornstein H-Zr*. DOI: 10.1007/10501684_1570  
  Authoritative compilation for Zr-H. Helps align phase-field assumptions and reference-state definitions across datasets.

- **ackland1998_zrh_bistable**: *Bistable crystal structure of zirconium hydride*. DOI: 10.1103/PhysRevLett.80.2233  
  Demonstrates structural complexity relevant to hydride stability and embrittlement context. Important for stage-4 hydride competition assumptions.

- **rees1954_interpretation_zr**: *Interpretation of the solubility of hydrogen in zirconium*. DOI: 10.1039/TF9545000343  
  Provides equation-based interpretation of Zr-H isotherms and phase-region behavior, including reported pressure-temperature relations. Useful for benchmark equation extraction and model sanity checks.

- **carsteanu2005_yh_lattice**: *Lattice distortion in YH2+delta / YH3-eta thin films*. DOI: 10.1016/j.jallcom.2004.09.091  
  Provides structural detail for Y hydrides near non-stoichiometric regimes. Useful context for defining hydride reference states in Y-side thermodynamics.

## 3) Key DFT studies on H in hcp Y and hcp Zr (site preference, solution energies)

- **udagawa2010_plane_defects**: *Ab initio study on Zr-H solid solution and hydride plane defects*. DOI: 10.1016/j.actamat.2010.03.034  
  Mechanistic first-principles treatment of Zr-H energetics and defects. Useful baseline for site energetics and defect-mediated behavior on the Zr side.

- **wang2020_strain_solution_energy**: *Strain effects on H solution energy in alpha-Zr*. DOI: 10.1016/j.ijhydene.2020.04.244  
  Quantifies elastic-strain coupling to hydrogen solution energy in alpha-Zr. Important for testing sensitivity of modeled solubility trends to local stress states.

- **zhu2010_zrh_polymorphs**: *First-principles study of zirconium hydride polymorphs*. DOI: 10.1021/jp109185n  
  Provides DFT energetics across ZrH polymorphs. Key input for stage-4 competing-phase free-energy landscape.

- **huang2019_alpha_zr_zrh_interface**: *Alpha-Zr / ZrH interfacial energies from first principles*. DOI: 10.1063/1.5102176  
  Adds interface energetics needed to interpret hydride nucleation/competition beyond bulk phase stability alone.

- **zhou2025_zr_microalloy_y**: *First-principles study of H diffusion and hydride transformation in Y with Zr microalloying*. DOI: 10.1016/j.jnucmat.2025.155919  
  Recent DFT-based source directly tied to H energetics/kinetics in Y-containing systems. Provides modern computational context for Y-side mechanistic trends.

- **lin2025_diffusion_yh**: *Hydrogen diffusion in yttrium hydrides via first-principles + MLMD*. DOI: 10.1016/j.ijhydene.2025.01.179  
  Extends Y-side understanding toward finite-temperature diffusion in hydride phases. Useful for linking static DFT energetics to temperature-dependent transport behavior.

- **liu1989_h_pairing_y**: *Theory of hydrogen pairing in yttrium*. DOI: 10.1103/PhysRevLett.63.1396  
  Early theoretical work proposing non-trivial H-H interactions in Y host environments. Useful as a mechanistic hypothesis source for concentration-dependent effects.

Current gap note: direct, systematic dilute-H site-energy studies in pure alpha-Y are still sparser than for alpha-Zr; this remains a high-priority gap for project-generated calculations.

## 4) Vibrational / ZPE / phonon methodology sources for H in metals

- **baroni2001_dfpt**: *DFPT review*. DOI: 10.1103/RevModPhys.73.515  
  Standard reference for lattice-dynamical properties from first principles. Provides rigorous basis for vibrational free-energy workflows.

- **parlinski1997_finite_displacement**: *Finite-displacement phonon methodology exemplar*. DOI: 10.1103/PhysRevLett.78.4063  
  Demonstrates force-constant extraction strategy used broadly in supercell phonon calculations. Supports practical implementation choices when DFPT is unavailable.

- **togo2015_phonopy**: *First-principles phonon calculations in materials science*. DOI: 10.1016/j.scriptamat.2015.07.021  
  Practical workflow reference for phonon post-processing and free-energy computation. Directly useful for stage-3 implementation templates.

- **fultz2010_vibrational_thermo**: *Vibrational thermodynamics of materials*. DOI: 10.1016/j.pmatsci.2009.05.002  
  Comprehensive thermodynamic interpretation of vibrational contributions. Useful for deciding when ZPE/finite-T corrections materially alter site/phase ordering.

## 5) Thermodynamic framework sources for mapping DFT energies to solubility

- **lacher1937_solubility_formula**: *Theoretical formula for H solubility in Pd*. DOI: 10.1098/rspa.1937.0160  
  Classic lattice-thermodynamic framework for interstitial hydrogen solution behavior. While not Y/Zr-specific, it provides conceptual grounding for dilute solution modeling.

- **flanagan1983_solvus**: *Solvus thermodynamics of metal-hydrogen interstitial solutions*. DOI: 10.1016/0001-6160(83)90079-2  
  Directly relevant framework for linking thermodynamics to solvus behavior. Supports model terms for configurational and non-ideal effects near precipitation boundaries.

- **hashino1976_interstitial_thermo**: *Thermodynamics of interstitial H solutions in metals*. DOI: 10.1063/1.432309  
  Offers derivational treatment of interstitial hydrogen thermodynamics. Useful for building transparent equations from DFT energies to concentration predictions.

- **perdew1996_pbe**, **blochl1994_paw**, **kresse1996_iterative**, **kresse1999_paw_vasp**. DOIs: 10.1103/PhysRevLett.77.3865, 10.1103/PhysRevB.50.17953, 10.1103/PhysRevB.54.11169, 10.1103/PhysRevB.59.1758  
  These are method-stack references for the electronic-structure baseline (functional + PAW + VASP solver). They define the numerical context of all computed energies feeding the thermodynamic model.

## 6) Open gaps + hypotheses to test

### High-priority gaps
- Sparse direct dilute-H DFT datasets in pure alpha-Y compared with alpha-Zr.
- Limited head-to-head free-energy comparison using identical computational settings across Y and Zr.
- Incomplete integration of hydride competition and vibrational corrections into one coherent c_H(T,p) model for both systems.

### Working hypotheses (to be tested)
- **H1 (solution energetics):** H insertion free energy in alpha-Y is significantly lower than in alpha-Zr over the same reference state choice.
- **H2 (entropy/vibrations):** Vibrational/ZPE corrections amplify the Y-vs-Zr solubility contrast rather than canceling it.
- **H3 (phase competition):** Hydride precipitation thermodynamics truncates dissolved-H regime earlier in Zr than in Y.
- **H4 (non-ideality):** Pairing/non-ideal interactions are stronger for H in Y at relevant concentrations and must be modeled beyond ideal dilute assumptions.

### Immediate evidence tasks
- Extract numeric TSS-vs-T targets from Section 1+2 sources into a machine-readable table.
- Build initial consistent DFT protocol to compute dilute-H site energetics in alpha-Y and alpha-Zr.
- Define explicit equation set for converting DFT energies + vibrational terms into predicted c_H(T,p).

## Machine-Readable Benchmark Outputs (Current)
- `literature/benchmarks/tss_benchmark_records.csv`: quantitative anchors and equation-based benchmark records with status tags.
- `literature/benchmarks/provenance_map.md`: per-record traceability to source equation/table/text locations.

Current status note:
- Initial extracted anchors are committed for both Y and Zr, including equation records and high-confidence text/table values.
- Direct full TSS/TSSP point-cloud digitization remains flagged as `needs_digitization` for strict curve-level benchmarking.
